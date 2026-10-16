"""
Vanessa - Central Orchestrator & Server.
Features:
- Tone-adaptive reasoning (Serious vs Playful/Sarcastic Maid)
- Passive wake word continuous listening ("Vanessa" / "Hey Jarvis")
- Faster-Whisper Speech-to-Text & Voice Emotion/Pitch Analyzer
- Edge-TTS natural voice output with lip-sync
- Facial biometrics with SFace ("Amo Víctor") & Object Recognition (NanoDet)
- Screen perception via Wayland grim (reviews code, videos, docs)
- Generative tools (Excel .xlsx, Word .docx, SQLite .db, Code files)
- Hardware controls & Computer Shutdown
- Auto-Sleep / Inactivity fade-out
"""
import os
import json
import asyncio
import threading
from typing import Set, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from core.memory import MemoryManager
from core.system_control import SystemController
from core.file_manager import FileManager
from core.music_detector import MusicDetector
from core.brain import AssistantBrain
from senses.vision import VisionObserver
from senses.wake_word import WakeWordDetector
from senses.speech_to_text import SpeechToText
from senses.text_to_speech import TextToSpeech
from senses.voice_biometrics import VoiceAnalyzer

# Subsystems
memory = MemoryManager()
sys_ctrl = SystemController(kbd_device="asus::kbd_backlight")
file_mgr = FileManager()
music_det = MusicDetector()
brain = AssistantBrain(memory, sys_ctrl, file_mgr, music_det)

vision = VisionObserver(camera_index=0, sample_interval=3.5)
stt = SpeechToText(model_size="base", device="cpu", compute_type="int8")
tts = TextToSpeech(voice="es-MX-DaliaNeural")
voice_analyzer = VoiceAnalyzer()

# Hook face enrollment from brain into vision sensor
def handle_face_enroll(name: str) -> bool:
    return vision.enroll_current_user(name)

brain.on_enroll_face_request = handle_face_enroll

# Connected WebSocket clients
connected_clients: Set[WebSocket] = set()
event_loop: asyncio.AbstractEventLoop = None

async def broadcast_ws(message: Dict[str, Any]):
    if not connected_clients:
        return
    disconnected = set()
    msg_str = json.dumps(message)
    for ws in connected_clients:
        try:
            await ws.send_text(msg_str)
        except Exception:
            disconnected.add(ws)
    connected_clients.difference_update(disconnected)

def run_coroutine(coro):
    global event_loop
    if event_loop and event_loop.is_running():
        asyncio.run_coroutine_threadsafe(coro, event_loop)

# Vision callback
last_proactive_comment_time = 0.0

def on_vision_update(state: Dict[str, Any]):
    global last_proactive_comment_time
    now = asyncio.get_event_loop().time() if event_loop else 0.0

    run_coroutine(broadcast_ws({
        "type": "state_update",
        "payload": {
            "vision": state,
            "toggles": {
                "microphone": wake_detector.is_active,
                "camera": vision.enabled
            },
            "wake_word_active": wake_detector.is_active
        }
    }))

    # Spontaneous greeting if Amo Victor is recognized and smiling
    if state.get("smiling") and (now - last_proactive_comment_time > 60.0):
        last_proactive_comment_time = now
        run_coroutine(trigger_proactive_reaction("¡Qué alegría verlo sonreír, Amo Víctor! ¿En qué puedo complacerlo ahora?"))

async def trigger_proactive_reaction(text: str):
    await broadcast_ws({
        "type": "chat_message",
        "payload": {"role": "assistant", "content": text, "mood": "happy"}
    })
    await broadcast_ws({
        "type": "assistant_speech_start",
        "payload": {"mood": "happy"}
    })
    await tts.speak(text)
    await broadcast_ws({
        "type": "assistant_speech_done",
        "payload": {}
    })

# Process user verbal query
async def handle_user_voice_interaction():
    try:
        wake_detector.pause()
        await broadcast_ws({
            "type": "chat_message",
            "payload": {"role": "assistant", "content": "A la escucha, Amo...", "mood": "playful"}
        })

        # Record audio
        loop = asyncio.get_event_loop()
        audio_data = await loop.run_in_executor(None, stt.record_until_silence)

        if len(audio_data) == 0:
            await broadcast_ws({"type": "assistant_speech_done", "payload": {}})
            wake_detector.resume()
            return

        # Voice Tone & Emotion Analysis (Serious vs Playful)
        tone_info = voice_analyzer.analyze_tone_and_emotion(audio_data)
        detected_tone = tone_info.get("tone", "playful")

        # Transcribe with Whisper
        user_text = await loop.run_in_executor(None, stt.transcribe_audio_array, audio_data)

        if not user_text or len(user_text.strip()) < 2:
            await broadcast_ws({"type": "assistant_speech_done", "payload": {}})
            wake_detector.resume()
            return

        # Show user message
        await broadcast_ws({
            "type": "chat_message",
            "payload": {"role": "user", "content": user_text}
        })

        # Process through Brain with tone modulation & recognized user
        visual_ctx = vision.get_summary()
        recognized_user = vision.current_state.get("recognized_user", "Amo Víctor")
        reply, mood, extra = await brain.generate_response(
            user_text,
            visual_ctx,
            detected_tone=detected_tone,
            recognized_user=recognized_user
        )

        # Broadcast reply
        await broadcast_ws({
            "type": "chat_message",
            "payload": {"role": "assistant", "content": reply, "mood": mood}
        })

        # Speak with lip-sync
        await broadcast_ws({
            "type": "assistant_speech_start",
            "payload": {"mood": mood}
        })
        await tts.speak(reply)
        await broadcast_ws({
            "type": "assistant_speech_done",
            "payload": {}
        })

    except Exception as e:
        print(f"[Main] Error en interacción por voz: {e}")
    finally:
        wake_detector.resume()

def on_wake_word():
    print("[WakeWord] 'Vanessa' detectada!")
    run_coroutine(handle_user_voice_interaction())

# Initialize WakeWord sense
wake_detector = WakeWordDetector(
    wake_word="hey_jarvis",
    threshold=0.45,
    on_wake=on_wake_word
)

vision.on_state_change_callback = on_vision_update

@asynccontextmanager
async def lifespan(app: FastAPI):
    global event_loop
    event_loop = asyncio.get_running_loop()

    # Start vision and wake word threads
    vision.start()
    wake_detector.start()
    sys_ctrl.show_desktop_notification("Vanessa Activa", "A su completo servicio, Amo Víctor.")
    print("[Vanessa] Sistema iniciado. Sensores de visión, biometría y wake word activos.")
    yield
    # Cleanup
    vision.stop()
    wake_detector.stop()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="ui/static"), name="static")

@app.get("/")
async def serve_index():
    return FileResponse("ui/index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)

    # Initial state
    await websocket.send_text(json.dumps({
        "type": "state_update",
        "payload": {
            "vision": vision.current_state,
            "toggles": {
                "microphone": wake_detector.is_active,
                "camera": vision.enabled
            },
            "wake_word_active": wake_detector.is_active
        }
    }))

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            msg_type = data.get("type")
            payload = data.get("payload", {})

            if msg_type == "user_message":
                text = payload.get("text", "")
                visual_ctx = vision.get_summary()
                recognized_user = vision.current_state.get("recognized_user", "Amo Víctor")
                reply, mood, extra = await brain.generate_response(
                    text,
                    visual_ctx,
                    detected_tone="playful",
                    recognized_user=recognized_user
                )

                await broadcast_ws({
                    "type": "chat_message",
                    "payload": {"role": "assistant", "content": reply, "mood": mood}
                })

                await broadcast_ws({
                    "type": "assistant_speech_start",
                    "payload": {"mood": mood}
                })
                await tts.speak(reply)
                await broadcast_ws({
                    "type": "assistant_speech_done",
                    "payload": {}
                })

            elif msg_type == "start_voice_capture":
                asyncio.create_task(handle_user_voice_interaction())

            elif msg_type == "toggle_hardware":
                device = payload.get("device")
                enabled = payload.get("enabled", True)
                if device == "camera":
                    vision.set_enabled(enabled)
                elif device == "microphone":
                    if enabled:
                        wake_detector.resume()
                    else:
                        wake_detector.pause()

            elif msg_type == "system_command":
                action = payload.get("action")
                if action == "analyze_screen":
                    advice_res = await brain.screen_obs.analyze_screen()
                    advice = advice_res.get("advice", "No pude capturar la pantalla.")
                    await broadcast_ws({"type": "chat_message", "payload": {"role": "assistant", "content": advice, "mood": "thinking"}})
                    await broadcast_ws({"type": "assistant_speech_start", "payload": {"mood": "thinking"}})
                    await tts.speak(advice)
                    await broadcast_ws({"type": "assistant_speech_done", "payload": {}})

                elif action == "generate_excel":
                    headers = ["ID", "Tarea", "Responsable", "Prioridad", "Estado"]
                    rows = [
                        [1, "Optimizar consumo RAM", "Vanessa", "Alta", "Completado"],
                        [2, "Revisar código en pantalla", "Amo Víctor", "Media", "En curso"],
                        [3, "Generación de artefactos", "Vanessa", "Alta", "Listo"]
                    ]
                    path = brain.generator.create_excel("Reporte_Actividades", headers, rows)
                    msg = f"Amo Víctor, he creado la hoja de cálculo en: {path}"
                    await broadcast_ws({"type": "chat_message", "payload": {"role": "assistant", "content": msg, "mood": "happy"}})
                    await tts.speak(msg)

                elif action == "check_objects":
                    recent_objs = brain.object_det.get_recent_detected_objects()
                    msg = f"Amo Víctor, identifico en su mesa: {', '.join(recent_objs) if recent_objs else 'sin objetos detectados'}"
                    await broadcast_ws({"type": "chat_message", "payload": {"role": "assistant", "content": msg, "mood": "happy"}})
                    await tts.speak(msg)

                elif action == "enroll_face":
                    success = vision.enroll_current_user("Amo Víctor")
                    msg = "¡Rostro memorizado con éxito! Siempre lo reconoceré, Amo Víctor." if success else "Amo, por favor mire fijamente a la cámara frontal para memorizar su rostro."
                    await broadcast_ws({"type": "chat_message", "payload": {"role": "assistant", "content": msg, "mood": "happy" if success else "thinking"}})
                    await tts.speak(msg)

                elif action == "shutdown_pc":
                    res = sys_ctrl.shutdown_computer()
                    await broadcast_ws({"type": "chat_message", "payload": {"role": "assistant", "content": res, "mood": "serious"}})
                    await tts.speak(res)

                elif action == "keyboard_light":
                    state = payload.get("state", "on")
                    res = sys_ctrl.set_keyboard_backlight(state)
                    await broadcast_ws({"type": "chat_message", "payload": {"role": "assistant", "content": res, "mood": "happy"}})
                elif action == "wifi_toggle":
                    cur = sys_ctrl.get_wifi_status()
                    new_state = "desactivado" in cur
                    res = sys_ctrl.set_wifi(new_state)
                    await broadcast_ws({"type": "chat_message", "payload": {"role": "assistant", "content": res, "mood": "happy"}})
                elif action == "bluetooth_toggle":
                    res = sys_ctrl.set_bluetooth(True)
                    await broadcast_ws({"type": "chat_message", "payload": {"role": "assistant", "content": res, "mood": "happy"}})
                elif action == "open_youtube":
                    res = sys_ctrl.open_youtube()
                    await broadcast_ws({"type": "chat_message", "payload": {"role": "assistant", "content": res, "mood": "happy"}})

            elif msg_type == "update_personality":
                new_name = payload.get("name")
                new_prompt = payload.get("system_prompt")
                new_style = payload.get("speech_style")

                p_path = "config/personality.json"
                try:
                    with open(p_path, "r", encoding="utf-8") as f:
                        curr_p = json.load(f)
                    if new_name: curr_p["name"] = new_name
                    if new_prompt: curr_p["system_prompt"] = new_prompt
                    if new_style: curr_p["speech_style"] = new_style
                    with open(p_path, "w", encoding="utf-8") as f:
                        json.dump(curr_p, f, indent=2, ensure_ascii=False)
                    brain.reload_config()
                except Exception as e:
                    print(f"Error actualizando personalidad: {e}")

    except WebSocketDisconnect:
        connected_clients.remove(websocket)

if __name__ == "__main__":
    port = 8765
    print(f"\n=======================================================")
    print(f"  🎀 VANESSA - ASISTENTE MAID PERSONAL INICIADA 🎀")
    print(f"  Panel Web: http://127.0.0.1:{port}")
    print(f"  Wake Word: 'Vanessa'")
    print(f"=======================================================\n")
    uvicorn.run("main:app", host="127.0.0.1", port=port, log_level="info")
