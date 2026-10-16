import os
import hashlib
from typing import Dict, Optional, Any
from PyQt6.QtCore import QObject, pyqtSignal

class AvatarLifecycleController(QObject):
    mode_changed = pyqtSignal(str)
    model_loaded = pyqtSignal(str, str)
    throttling_changed = pyqtSignal(bool, int)

    def __init__(self, overlay=None):
        parent_obj = overlay if isinstance(overlay, QObject) else None
        super().__init__(parent_obj)
        self.overlay = overlay
        self.current_mode = "standard"
        self.is_throttled = False
        self.throttle_fps = 15
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.vrm_models_map: Dict[str, str] = {}
        self.current_model_key = "vanessa"
        self._initialize_catalog()

    def _initialize_catalog(self):
        models_dir = os.path.join(self.base_dir, "ui/static/vrm_models")
        default_map = {
            "vanessa": os.path.join(models_dir, "Vanessa_Flagship_Anime.vrm"),
            "ellen": os.path.join(models_dir, "Ellen_Joe_Maid.vrm"),
            "nicole": os.path.join(models_dir, "Nicole_Demara.vrm"),
            "anby": os.path.join(models_dir, "Anby_Demara.vrm"),
            "jane": os.path.join(models_dir, "Jane_Doe_Thiren.vrm"),
            "miyabi": os.path.join(models_dir, "Hoshimi_Miyabi_Section6.vrm"),
            "billy": os.path.join(models_dir, "Billy_Kid_Starlight.vrm"),
            "belle": os.path.join(models_dir, "Belle_Proxy.vrm"),
            "kira": os.path.join(models_dir, "Kira_Urban_Anime.vrm"),
            "aoi": os.path.join(models_dir, "Aoi_Cyber_Anime.vrm"),
            "kuro": os.path.join(models_dir, "Kuro_Goth_Anime.vrm"),
            "orion": os.path.join(models_dir, "Orion_SciFi_Anime.vrm"),
        }
        self.vrm_models_map = {k: p for k, p in default_map.items() if os.path.exists(p)}
        seen_hashes = {}
        for k, p in list(self.vrm_models_map.items()):
            try:
                with open(p, "rb") as fp:
                    h = hashlib.sha256(fp.read(1048576)).hexdigest()
                    seen_hashes[h] = k
            except Exception:
                pass

        if os.path.exists(models_dir):
            for root, dirs, files in os.walk(models_dir):
                for fname in sorted(files):
                    name_lower = fname.lower()
                    if name_lower.endswith((".vrm", ".gltf", ".glb", ".fbx", ".pmx")) and not any(fname.startswith(p) for p in ("武器", "刀", "幽灵", "left", "right", "òÇ", "透過無")):
                        fpath = os.path.join(root, fname)
                        try:
                            with open(fpath, "rb") as fp:
                                h = hashlib.sha256(fp.read(1048576)).hexdigest()
                            if h not in seen_hashes:
                                key = os.path.splitext(fname)[0].lower()
                                self.vrm_models_map[key] = fpath
                                seen_hashes[h] = key
                        except Exception:
                            pass

        pmx_dirs = [
            os.path.join(self.base_dir, "models/pmx_models"),
            os.path.join(self.base_dir, "ui/static/pmx_models")
        ]
        for p_dir in pmx_dirs:
            if os.path.exists(p_dir):
                for root, dirs, files in os.walk(p_dir):
                    for fname in sorted(files):
                        if fname.lower().endswith(".pmx") and not any(fname.startswith(p) for p in ("武器", "刀", "幽灵")):
                            fpath = os.path.join(root, fname)
                            try:
                                with open(fpath, "rb") as fp:
                                    h = hashlib.sha256(fp.read(1048576)).hexdigest()
                                if h not in seen_hashes:
                                    key = os.path.splitext(fname)[0].lower()
                                    self.vrm_models_map[key] = fpath
                                    seen_hashes[h] = key
                            except Exception:
                                pass

    def set_avatar_mode(self, mode: str):
        mode_clean = "chibi" if mode == "chibi" else "standard"
        self.current_mode = mode_clean
        if hasattr(self.overlay, "vrm_widget") and self.overlay.vrm_widget:
            self.overlay.vrm_widget.set_avatar_mode(mode_clean)
        self.mode_changed.emit(mode_clean)

    def toggle_avatar_mode(self):
        new_mode = "chibi" if self.current_mode == "standard" else "standard"
        self.set_avatar_mode(new_mode)
        return new_mode

    def set_throttling(self, throttled: bool, fps: int = 15):
        self.is_throttled = bool(throttled)
        self.throttle_fps = int(fps)
        if hasattr(self.overlay, "vrm_widget") and self.overlay.vrm_widget:
            self.overlay.vrm_widget.set_throttling(self.is_throttled, self.throttle_fps)
        self.throttling_changed.emit(self.is_throttled, self.throttle_fps)

    def load_model(self, key_or_path: str):
        target_path = ""
        if os.path.isabs(key_or_path) and os.path.exists(key_or_path):
            target_path = key_or_path
            key = os.path.splitext(os.path.basename(key_or_path))[0].lower()
            self.vrm_models_map[key] = target_path
            self.current_model_key = key
        elif key_or_path in self.vrm_models_map:
            target_path = self.vrm_models_map[key_or_path]
            self.current_model_key = key_or_path
        elif self.vrm_models_map:
            first_key = list(self.vrm_models_map.keys())[0]
            target_path = self.vrm_models_map[first_key]
            self.current_model_key = first_key

        if target_path and hasattr(self.overlay, "vrm_widget") and self.overlay.vrm_widget:
            self.overlay.vrm_widget.load_model(target_path)
            self.model_loaded.emit(self.current_model_key, target_path)

    def get_available_models(self) -> Dict[str, str]:
        return dict(self.vrm_models_map)
