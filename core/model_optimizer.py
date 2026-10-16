import os
import json
import hashlib

OFFICIAL_ZZZ_MODELS = {
    "burnice_white": {
        "model_id": "burnice_white",
        "display_name": "Burnice White",
        "faction": "Sons of Calydon",
        "role": "Fire / Anomaly Specialist",
        "primary_file": "burnice_white.pmx",
        "scale": 0.090,
        "camera_distance": 2.75,
        "hips_y": 1.04,
        "arm_rest": {
            "left": [0.12, 0.04, -1.22],
            "right": [0.12, -0.04, 1.22]
        },
        "forearm_rest": {
            "left": [0.20, 0.00, 0.15],
            "right": [0.20, 0.00, -0.15]
        },
        "description": "Oficial Zenless Zone Zero - Burnice White con shaders anime de alta fidelidad."
    },
    "ellen_joe": {
        "model_id": "ellen_joe",
        "display_name": "Ellen Joe",
        "faction": "Victoria Housekeeping Co.",
        "role": "Ice / Attack Specialist Maid",
        "primary_file": "ellen_joe.pmx",
        "scale": 0.088,
        "camera_distance": 2.85,
        "hips_y": 1.08,
        "arm_rest": {
            "left": [0.10, 0.05, -1.25],
            "right": [0.10, -0.05, 1.25]
        },
        "forearm_rest": {
            "left": [0.18, 0.00, 0.12],
            "right": [0.18, 0.00, -0.12]
        },
        "description": "Oficial Zenless Zone Zero - Ellen Joe con atuendo maid y cola estabilizada."
    },
    "jane_doe": {
        "model_id": "jane_doe",
        "display_name": "Jane Doe",
        "faction": "Criminal Investigation Special Response Team",
        "role": "Physical / Anomaly Thiren",
        "primary_file": "jane_doe.pmx",
        "scale": 0.087,
        "camera_distance": 2.70,
        "hips_y": 1.02,
        "arm_rest": {
            "left": [0.11, 0.04, -1.20],
            "right": [0.11, -0.04, 1.20]
        },
        "forearm_rest": {
            "left": [0.22, 0.00, 0.14],
            "right": [0.22, 0.00, -0.14]
        },
        "description": "Oficial Zenless Zone Zero - Jane Doe con cinemática thiren y articulación suave."
    },
    "anby_demara": {
        "model_id": "anby_demara",
        "display_name": "Anby Demara",
        "faction": "Cunning Hares",
        "role": "Electric / Stun Specialist",
        "primary_file": "anby_demara.pmx",
        "scale": 0.086,
        "camera_distance": 2.65,
        "hips_y": 0.98,
        "arm_rest": {
            "left": [0.10, 0.05, -1.22],
            "right": [0.10, -0.05, 1.22]
        },
        "forearm_rest": {
            "left": [0.19, 0.00, 0.12],
            "right": [0.19, 0.00, -0.12]
        },
        "description": "Oficial Zenless Zone Zero - Anby Demara con audífonos y accesorios dinámicos."
    },
    "nicole_demara": {
        "model_id": "nicole_demara",
        "display_name": "Nicole Demara",
        "faction": "Cunning Hares",
        "role": "Ether / Support Leader",
        "primary_file": "nicole_demara.pmx",
        "scale": 0.089,
        "camera_distance": 2.80,
        "hips_y": 1.06,
        "arm_rest": {
            "left": [0.13, 0.04, -1.24],
            "right": [0.13, -0.04, 1.24]
        },
        "forearm_rest": {
            "left": [0.21, 0.00, 0.16],
            "right": [0.21, 0.00, -0.16]
        },
        "description": "Oficial Zenless Zone Zero - Nicole Demara con coleta y abrigo con físicas estables."
    },
    "hoshimi_miyabi": {
        "model_id": "hoshimi_miyabi",
        "display_name": "Hoshimi Miyabi",
        "faction": "Section 6 (Hollow Special Operations)",
        "role": "Ice / Anomaly Section Leader",
        "primary_file": "hoshimi_miyabi.pmx",
        "scale": 0.088,
        "camera_distance": 2.75,
        "hips_y": 1.03,
        "arm_rest": {
            "left": [0.10, 0.05, -1.23],
            "right": [0.10, -0.05, 1.23]
        },
        "forearm_rest": {
            "left": [0.18, 0.00, 0.13],
            "right": [0.18, 0.00, -0.13]
        },
        "description": "Oficial Zenless Zone Zero - Hoshimi Miyabi con cabello largo y orejas de zorro animadas."
    }
}

USER_HOLOLIVE_MODELS = {
    "hoshimachi_suisei": {
        "model_id": "hoshimachi_suisei",
        "display_name": "Hoshimachi Suisei (Maid)",
        "faction": "Hololive 0th Gen / Maid Special",
        "role": "Stellar Vocalist & Flagship Maid",
        "primary_file": "hoshimachi_suisei.pmx",
        "folder_alias": "É»èXé╖éóé╣éóâüâCâhê▀æòMMD",
        "scale": 0.086,
        "camera_distance": 2.75,
        "hips_y": 1.05,
        "arm_rest": {
            "left": [0.12, 0.04, -1.22],
            "right": [0.12, -0.04, 1.22]
        },
        "forearm_rest": {
            "left": [0.20, 0.00, 0.15],
            "right": [0.20, 0.00, -0.15]
        },
        "description": "Hoshimachi Suisei con atuendo maid de gala, boina y lazo estelar."
    },
    "houshou_marine": {
        "model_id": "houshou_marine",
        "display_name": "Houshou Marine (V2)",
        "faction": "Hololive Fantasy (3rd Gen)",
        "role": "Ahoy! Pirate Captain",
        "primary_file": "houshou_marine.pmx",
        "folder_alias": "HoushouMarine",
        "scale": 0.088,
        "camera_distance": 2.75,
        "hips_y": 1.02,
        "arm_rest": {
            "left": [0.10, 0.05, -1.24],
            "right": [0.10, -0.05, 1.24]
        },
        "forearm_rest": {
            "left": [0.18, 0.00, 0.12],
            "right": [0.18, 0.00, -0.12]
        },
        "description": "Houshou Marine V2 con sombrero pirata, capa dorada y shaders 4K."
    },
    "inugami_korone": {
        "model_id": "inugami_korone",
        "display_name": "Inugami Korone",
        "faction": "Hololive GAMERS",
        "role": "Doog Baker & Energetic Gamer",
        "primary_file": "inugami_korone.pmx",
        "folder_alias": "InugamiKorone",
        "scale": 0.090,
        "camera_distance": 2.70,
        "hips_y": 0.98,
        "arm_rest": {
            "left": [0.11, 0.04, -1.20],
            "right": [0.11, -0.04, 1.20]
        },
        "forearm_rest": {
            "left": [0.20, 0.00, 0.14],
            "right": [0.20, 0.00, -0.14]
        },
        "description": "Inugami Korone con orejas caninas, cola animada y pasador de hueso."
    },
    "nekomata_okayu": {
        "model_id": "nekomata_okayu",
        "display_name": "Nekomata Okayu",
        "faction": "Hololive GAMERS",
        "role": "Chill Cat Onigiri Lover",
        "primary_file": "nekomata_okayu.pmx",
        "folder_alias": "öLûöé¿é⌐éΣî÷Ä«mmd_ver1.0",
        "scale": 0.088,
        "camera_distance": 2.75,
        "hips_y": 1.03,
        "arm_rest": {
            "left": [0.10, 0.04, -1.22],
            "right": [0.10, -0.04, 1.22]
        },
        "forearm_rest": {
            "left": [0.19, 0.00, 0.13],
            "right": [0.19, 0.00, -0.13]
        },
        "description": "Nekomata Okayu con orejas de gato, sudadera holgada y expresión relajada."
    },
    "tsunomaki_watame": {
        "model_id": "tsunomaki_watame",
        "display_name": "Tsunomaki Watame",
        "faction": "Hololive 4th Gen",
        "role": "Fluffy Bard & Harping Sheep",
        "primary_file": "tsunomaki_watame.pmx",
        "folder_alias": "èpè¬éφé╜é▀î÷Ä«mmd_ver1.0",
        "scale": 0.089,
        "camera_distance": 2.70,
        "hips_y": 1.00,
        "arm_rest": {
            "left": [0.12, 0.04, -1.22],
            "right": [0.12, -0.04, 1.22]
        },
        "forearm_rest": {
            "left": [0.18, 0.00, 0.12],
            "right": [0.18, 0.00, -0.12]
        },
        "description": "Tsunomaki Watame con cuernos espirales, capa afelpada y cascabel."
    },
    "ouro_kronii": {
        "model_id": "ouro_kronii",
        "display_name": "Ouro Kronii",
        "faction": "Hololive English -Council- / Promise",
        "role": "Warden of Time",
        "primary_file": "ouro_kronii.pmx",
        "folder_alias": "OuroKronii",
        "scale": 0.075,
        "camera_distance": 2.95,
        "hips_y": 1.15,
        "arm_rest": {
            "left": [0.08, 0.05, -1.26],
            "right": [0.08, -0.05, 1.26]
        },
        "forearm_rest": {
            "left": [0.16, 0.00, 0.10],
            "right": [0.16, 0.00, -0.10]
        },
        "description": "Ouro Kronii Guardiana del Tiempo con tocado de manecillas y capa asimétrica."
    },
    "pavolia_reine": {
        "model_id": "pavolia_reine",
        "display_name": "Pavolia Reine",
        "faction": "Hololive Indonesia 2nd Gen (holoro)",
        "role": "Peafowl Princess",
        "primary_file": "pavolia_reine.pmx",
        "folder_alias": "PavoliaReine",
        "scale": 0.084,
        "camera_distance": 2.80,
        "hips_y": 1.06,
        "arm_rest": {
            "left": [0.10, 0.05, -1.24],
            "right": [0.10, -0.05, 1.24]
        },
        "forearm_rest": {
            "left": [0.18, 0.00, 0.12],
            "right": [0.18, 0.00, -0.12]
        },
        "description": "Pavolia Reine con plumaje real de pavo real, vestido de alta costura y peinado lateral."
    },
    "hatsune_miku_v4c": {
        "model_id": "hatsune_miku_v4c",
        "display_name": "Hatsune Miku V4C (野餐式)",
        "faction": "Vocaloid / Crypton Future Media",
        "role": "Virtual Diva & Global Idol",
        "primary_file": "v4c7.3.pmx",
        "folder_alias": "野餐式v4c",
        "scale": 0.088,
        "camera_distance": 2.75,
        "hips_y": 1.02,
        "arm_rest": {
            "left": [0.10, 0.05, -1.24],
            "right": [0.10, -0.05, 1.24]
        },
        "forearm_rest": {
            "left": [0.18, 0.00, 0.12],
            "right": [0.18, 0.00, -0.12]
        },
        "description": "Hatsune Miku V4C por Picnic con coletas dobles icónicas, atuendo cibernético y corbata cian."
    }
}

class ModelOptimizer:
    def __init__(self, base_models_dir=None):
        if base_models_dir is None:
            self.base_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "models", "pmx_models")
            )
        else:
            self.base_dir = os.path.abspath(base_models_dir)

    def optimize_all_models(self):
        results = {}
        for model_id, meta in OFFICIAL_ZZZ_MODELS.items():
            model_dir = os.path.join(self.base_dir, model_id)
            if not os.path.exists(model_dir):
                continue
            optimized_meta = self.optimize_model(model_id, model_dir, meta)
            results[model_id] = optimized_meta
        return results

    def optimize_model(self, model_id, model_dir, meta):
        pmx_path = os.path.join(model_dir, meta["primary_file"])
        if not os.path.exists(pmx_path):
            candidates = [f for f in os.listdir(model_dir) if f.endswith(".pmx") and not any(f.startswith(p) for p in ("武器", "刀", "幽灵"))]
            if candidates:
                pmx_path = os.path.join(model_dir, candidates[0])
            else:
                return None

        file_hash = ""
        try:
            with open(pmx_path, "rb") as fp:
                file_hash = hashlib.sha256(fp.read(1048576)).hexdigest()
        except Exception:
            pass

        self._fix_texture_casing(model_dir)

        profile = dict(meta)
        profile["pmx_absolute_path"] = pmx_path
        profile["pmx_relative_path"] = f"/models/pmx_models/{model_id}/{os.path.basename(pmx_path)}"
        profile["file_hash"] = file_hash
        profile["file_size"] = os.path.getsize(pmx_path)

        profile_path = os.path.join(model_dir, "model_profile.json")
        try:
            with open(profile_path, "w", encoding="utf-8") as fp:
                json.dump(profile, fp, indent=2, ensure_ascii=False)
        except Exception:
            pass

        return profile

    def _fix_texture_casing(self, model_dir):
        for sub in ("tex", "textures", "spa"):
            sub_path = os.path.join(model_dir, sub)
            if os.path.isdir(sub_path):
                for fname in os.listdir(sub_path):
                    fpath = os.path.join(sub_path, fname)
                    lower_name = fname.lower()
                    lower_path = os.path.join(sub_path, lower_name)
                    if lower_name != fname and not os.path.exists(lower_path):
                        try:
                            os.symlink(fpath, lower_path)
                        except Exception:
                            pass

    def get_official_catalog(self):
        catalog = {}
        for model_id, meta in OFFICIAL_ZZZ_MODELS.items():
            model_dir = os.path.join(self.base_dir, model_id)
            pmx_path = os.path.join(model_dir, meta["primary_file"])
            if os.path.exists(pmx_path):
                item = dict(meta)
                item["pmx_path"] = pmx_path
                item["web_path"] = f"/models/pmx_models/{model_id}/{meta['primary_file']}"
                catalog[model_id] = item
        return catalog

    def get_user_models_catalog(self):
        user_models_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "ui", "static", "vrm_models")
        )
        catalog = {}
        for model_id, meta in USER_HOLOLIVE_MODELS.items():
            model_dir = os.path.join(user_models_dir, model_id)
            if not os.path.exists(model_dir):
                alias = meta.get("folder_alias")
                if alias:
                    model_dir = os.path.join(user_models_dir, alias)
            if not os.path.exists(model_dir):
                continue
            pmx_path = os.path.join(model_dir, meta["primary_file"])
            if not os.path.exists(pmx_path):
                candidates = [f for f in os.listdir(model_dir) if f.endswith(".pmx") and not any(f.startswith(p) for p in ("left", "right", "òÇ", "透過無"))]
                if candidates:
                    pmx_path = os.path.join(model_dir, candidates[0])
            if os.path.exists(pmx_path):
                item = dict(meta)
                item["pmx_path"] = pmx_path
                item["web_path"] = f"/ui/static/vrm_models/{model_id}/{os.path.basename(pmx_path)}"
                catalog[model_id] = item
                self.optimize_model(model_id, model_dir, meta)

        pmx_models_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "ui", "static", "pmx_models")
        )
        fallback_models_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "models", "pmx_models")
        )
        for model_id, meta in OFFICIAL_ZZZ_MODELS.items():
            model_dir = os.path.join(pmx_models_dir, model_id)
            if not os.path.exists(model_dir):
                model_dir = os.path.join(fallback_models_dir, model_id)
            if not os.path.exists(model_dir):
                continue
            pmx_path = os.path.join(model_dir, meta.get("primary_file", ""))
            if not os.path.exists(pmx_path):
                candidates = [f for f in os.listdir(model_dir) if f.endswith(".pmx") and not any(f.startswith(p) for p in ("武器", "刀", "幽灵"))]
                if candidates:
                    pmx_path = os.path.join(model_dir, candidates[0])
            if os.path.exists(pmx_path):
                item = dict(meta)
                item["pmx_path"] = pmx_path
                rel_web = os.path.relpath(pmx_path, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
                item["web_path"] = "/" + rel_web.replace("\\", "/")
                catalog[model_id] = item
        return catalog
