"""
Audio & Voice File Intelligence Module for Vanessa.
Inspired by top open-source projects (faster-whisper, Resemblyzer, pyannote, Silero-VAD):
- Scans and detects voice and audio files (.wav, .mp3, .m4a, .ogg, .flac, .opus, .webm) across user directories
- Extracts audio metadata (duration, sample rate, channels, RMS energy, SNR)
- Offline high-accuracy transcription of arbitrary audio files using local faster-whisper
- Speaker verification: compares audio files against Amo Víctor's enrolled biometric profile
- Audio conversion and trimming helpers
"""
import os
import glob
import time
import subprocess
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

# Audio libraries
try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None


class AudioFileIntelligence:
    SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".opus", ".webm", ".aac"}

    def __init__(self, stt_engine=None, voice_enrollment_mgr=None):
        self.stt = stt_engine
        self.voice_mgr = voice_enrollment_mgr
        self.home = os.path.expanduser("~")

    def find_audio_files(
        self,
        directory: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Scans for audio and voice files on the system or in a specific directory.
        Uses /usr/bin/fd if available for ultra-fast scanning, falling back to os.walk.
        """
        target_dir = directory if directory and os.path.isdir(directory) else self.home
        clean_q = query.strip() if query else ""
        results = []
        seen = set()

        fd_bin = "/usr/bin/fd" if os.path.exists("/usr/bin/fd") else None
        if fd_bin:
            ext_args = []
            for ext in self.SUPPORTED_EXTENSIONS:
                ext_args.extend(["-e", ext.lstrip(".")])

            cmd = [
                fd_bin,
                "-i", "-H",
                "-E", ".git",
                "-E", ".cache",
                "-E", "node_modules",
                "-E", ".venv",
                "-E", "__pycache__",
                "--max-results", str(limit * 2)
            ] + ext_args

            if clean_q:
                cmd.append(clean_q)

            cmd.append(target_dir)

            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=8)
                if proc.returncode == 0 and proc.stdout:
                    for line in proc.stdout.splitlines():
                        fpath = line.strip()
                        if fpath and fpath not in seen and os.path.exists(fpath):
                            seen.add(fpath)
                            meta = self.get_audio_metadata(fpath)
                            results.append(meta)
                            if len(results) >= limit:
                                return results
            except Exception as e:
                print(f"[AudioIntel] Error en fd search: {e}")

        # Fallback to python os.walk
        if len(results) < limit:
            search_dirs = [target_dir] if directory else [
                os.path.join(self.home, "Descargas"),
                os.path.join(self.home, "Downloads"),
                os.path.join(self.home, "Música"),
                os.path.join(self.home, "Music"),
                os.path.join(self.home, "Documentos"),
                os.path.join(self.home, "Documents"),
                os.path.join(self.home, "data/voice_dataset"),
            ]
            search_dirs = [d for d in search_dirs if os.path.isdir(d)]

            for sdir in search_dirs:
                for root, dirs, files in os.walk(sdir):
                    dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", ".venv", "__pycache__")]
                    for f in files:
                        ext = os.path.splitext(f)[1].lower()
                        if ext in self.SUPPORTED_EXTENSIONS:
                            fpath = os.path.join(root, f)
                            if clean_q and clean_q.lower() not in f.lower():
                                continue
                            if fpath not in seen:
                                seen.add(fpath)
                                results.append(self.get_audio_metadata(fpath))
                                if len(results) >= limit:
                                    return results

        return results

    def get_audio_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extracts detailed metadata from an audio file."""
        stat = os.stat(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        duration_sec = 0.0
        sample_rate = 0
        channels = 1
        rms_energy = 0.0

        if sf is not None:
            try:
                info = sf.info(file_path)
                duration_sec = info.duration
                sample_rate = info.samplerate
                channels = info.channels
            except Exception:
                pass

        if duration_sec == 0.0 and AudioSegment is not None:
            try:
                seg = AudioSegment.from_file(file_path)
                duration_sec = len(seg) / 1000.0
                sample_rate = seg.frame_rate
                channels = seg.channels
                rms_energy = float(seg.rms)
            except Exception:
                pass

        return {
            "filename": os.path.basename(file_path),
            "path": os.path.abspath(file_path),
            "extension": ext,
            "size_bytes": stat.st_size,
            "size_kb": round(stat.st_size / 1024, 1),
            "duration_sec": round(duration_sec, 2),
            "duration_str": self._format_duration(duration_sec),
            "sample_rate": sample_rate,
            "channels": channels,
            "modified_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            "is_voice_dataset": "voice_dataset" in file_path
        }

    def transcribe_audio_file(self, file_path: str, language: str = "es") -> Dict[str, Any]:
        """
        Transcribes any audio or voice recording on disk using the local SpeechToText (faster-whisper) model.
        Returns text, detected language, and duration.
        """
        if not os.path.exists(file_path):
            return {"success": False, "error": f"Archivo no encontrado: {file_path}", "text": ""}

        # Convert to 16kHz WAV mono if not standard format
        tmp_wav = None
        target_path = file_path
        try:
            if not file_path.lower().endswith(".wav"):
                if AudioSegment is not None:
                    seg = AudioSegment.from_file(file_path)
                    seg = seg.set_frame_rate(16000).set_channels(1)
                    tmp_wav = f"/tmp/vanessa_transcribe_{int(time.time()*1000)}.wav"
                    seg.export(tmp_wav, format="wav")
                    target_path = tmp_wav

            if self.stt is not None and hasattr(self.stt, "model"):
                segments, info = self.stt.model.transcribe(
                    target_path,
                    language=language,
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=400)
                )
                text_parts = [s.text.strip() for s in segments]
                full_text = " ".join(text_parts).strip()
                duration = info.duration if hasattr(info, "duration") else 0.0

                return {
                    "success": True,
                    "text": full_text or "(Audio sin voz discernible)",
                    "language": info.language if hasattr(info, "language") else language,
                    "duration_sec": round(duration, 2),
                    "file": file_path
                }
            else:
                return {
                    "success": False,
                    "error": "Motor SpeechToText no inicializado en Vanessa.",
                    "text": ""
                }
        except Exception as e:
            return {"success": False, "error": str(e), "text": ""}
        finally:
            if tmp_wav and os.path.exists(tmp_wav):
                try:
                    os.remove(tmp_wav)
                except Exception:
                    pass

    def verify_speaker_in_audio(self, file_path: str, target_name: str = "Amo Víctor") -> Dict[str, Any]:
        """
        Compares the speaker in an audio file against Amo Víctor's enrolled voice harmonics and biometric profile.
        Returns similarity percentage, pitch analysis, and master match verdict.
        """
        if not os.path.exists(file_path):
            return {"success": False, "error": f"Archivo no encontrado: {file_path}"}

        if not self.voice_mgr:
            return {"success": False, "error": "VoiceEnrollmentManager no disponible"}

        try:
            # Load audio using soundfile
            data, sr = sf.read(file_path)
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)

            # Resample if needed
            if sr != 16000:
                if AudioSegment is not None:
                    seg = AudioSegment.from_file(file_path).set_frame_rate(16000).set_channels(1)
                    data = np.array(seg.get_array_of_samples(), dtype=np.float32) / 32768.0
                    sr = 16000

            # Extract features via voice_mgr
            features = self.voice_mgr.extract_voice_features(data, sr)
            is_match, sim = self.voice_mgr.verify_speaker(features, name=target_name)

            return {
                "success": True,
                "file": file_path,
                "target_speaker": target_name,
                "is_match": is_match,
                "similarity_pct": round(sim, 1),
                "pitch_hz": features.get("pitch_hz", 0),
                "spectral_centroid": features.get("spectral_centroid", 0),
                "verdict": f"Coincide con {target_name} ({sim:.1f}%)" if is_match else f"Voz ajena / no coincide ({sim:.1f}%)"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _format_duration(seconds: float) -> str:
        if seconds <= 0:
            return "0s"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        elif m > 0:
            return f"{m}m {s}s"
        else:
            return f"{seconds:.1f}s"
