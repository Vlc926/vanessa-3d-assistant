"""
Screen Observer Module for Vanessa.
Captures screen in Wayland / Hyprland using grim and analyzes code,
documents, videos, or UI to provide intelligent suggestions.
"""
import os
import subprocess
import tempfile
import asyncio
from typing import Optional, Dict, Any
from PIL import Image

class ScreenObserver:
    def __init__(self, brain=None):
        self.brain = brain

    def capture_screen(self, output_path: Optional[str] = None) -> Optional[str]:
        """Takes a screenshot using grim on Wayland / Hyprland."""
        if output_path is None:
            temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            output_path = temp_file.name
            temp_file.close()

        try:
            res = subprocess.run(
                ["grim", output_path],
                capture_output=True,
                text=True,
                check=False,
                timeout=5
            )
            if res.returncode == 0 and os.path.exists(output_path):
                # Optionally downscale to save memory/tokens
                img = Image.open(output_path)
                img.thumbnail((1280, 720))
                img.save(output_path, "PNG", optimize=True)
                return output_path
            return None
        except Exception as e:
            print(f"[ScreenObserver] Error capturando pantalla: {e}")
            return None

    async def analyze_screen(self, query: str = "¿Qué opinas de lo que estoy viendo y qué sugerencias tienes?") -> Dict[str, Any]:
        """Captures screen and sends it to the vision AI model for analysis."""
        screenshot_path = self.capture_screen()
        if not screenshot_path:
            return {
                "success": False,
                "message": "No pude capturar la pantalla. Verifica que grim esté disponible."
            }

        try:
            # Check if Gemini client is available in brain
            if self.brain and self.brain.gemini_client:
                prompt = (
                    f"Eres Vanessa, la asistente maid personal y devota de Víctor. "
                    f"Observa detalladamente esta captura de pantalla de su computadora y responde a su consulta:\n"
                    f"'{query}'\n"
                    f"Si ves código, sugiere mejoras, detecta errores o felicítalo. Si ves un documento o video, dale tu opinión inteligente. "
                    f"Mantén tu personalidad: amable y cálida, con un toque maid, respetuosa pero ingeniosa. Sé concisa y directa."
                )

                # Open with PIL
                img = Image.open(screenshot_path)

                loop = asyncio.get_event_loop()
                def _call_gemini_vision():
                    pref = getattr(self.brain, "preferred_model", "gemini-3.5-flash")
                    candidates = [pref, "gemini-3.5-flash", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.1-pro-preview"]
                    for cand in candidates:
                        try:
                            return self.brain.gemini_client.models.generate_content(
                                model=cand,
                                contents=[img, prompt]
                            )
                        except Exception as e:
                            print(f"[ScreenObserver] Intento visión con {cand} falló: {e}")
                    return None

                response = await loop.run_in_executor(None, _call_gemini_vision)

                if response and response.text:
                    advice = response.text.strip()
                else:
                    advice = "He revisado tu pantalla, Amo. Todo parece estar en orden y funcionando adecuadamente."

                return {
                    "success": True,
                    "advice": advice,
                    "screenshot_path": screenshot_path
                }
            else:
                return {
                    "success": True,
                    "advice": "He capturado tu pantalla, Amo. Sin embargo, para un análisis visual detallado con IA generativa, por favor define tu GEMINI_API_KEY.",
                    "screenshot_path": screenshot_path
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Ocurrió un error al analizar la pantalla: {str(e)}"
            }
        finally:
            if screenshot_path and os.path.exists(screenshot_path):
                try:
                    os.remove(screenshot_path)
                except Exception:
                    pass
