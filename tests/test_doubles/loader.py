import importlib

def get_socket_reader_class():
    try:
        mod = importlib.import_module("src.perception.socket_reader")
        return getattr(mod, "SocketReader")
    except Exception:
        from tests.test_doubles.double_socket_reader import SocketReaderDouble
        return SocketReaderDouble

def get_hypr_client_class():
    try:
        mod = importlib.import_module("src.perception.hypr_client")
        return getattr(mod, "HyprClient")
    except Exception:
        from tests.test_doubles.double_hypr_client import HyprClientDouble
        return HyprClientDouble

def get_geometry_projector_class():
    try:
        mod = importlib.import_module("src.perception.geometry_projector")
        return getattr(mod, "GeometryProjector")
    except Exception:
        from tests.test_doubles.double_geometry_projector import GeometryProjectorDouble
        return GeometryProjectorDouble

def get_actuator_class():
    try:
        mod = importlib.import_module("src.perception.actuator")
        return getattr(mod, "Actuator")
    except Exception:
        from tests.test_doubles.double_actuator import ActuatorDouble
        return ActuatorDouble

def get_ipc_server_class():
    try:
        mod = importlib.import_module("src.perception.ipc_server")
        return getattr(mod, "IPCServer")
    except Exception:
        from tests.test_doubles.double_ipc_server import IPCServerDouble
        return IPCServerDouble

def get_ipc_client_class():
    try:
        mod = importlib.import_module("src.visual.ipc_client")
        return getattr(mod, "IPCClient")
    except Exception:
        from tests.test_doubles.double_ipc_client import IPCClientDouble
        return IPCClientDouble

def get_overlay_window_class():
    try:
        mod = importlib.import_module("src.visual.overlay_window")
        return getattr(mod, "OverlayWindow")
    except Exception:
        from tests.test_doubles.double_overlay_window import OverlayWindowDouble
        return OverlayWindowDouble

def get_two_bone_ik_class():
    try:
        mod = importlib.import_module("src.visual.two_bone_ik")
        return getattr(mod, "TwoBoneIKSolver")
    except Exception:
        from tests.test_doubles.double_two_bone_ik import TwoBoneIKSolverDouble
        return TwoBoneIKSolverDouble

def get_foot_lock_class():
    try:
        mod = importlib.import_module("src.visual.foot_lock")
        return getattr(mod, "FootLockController")
    except Exception:
        from tests.test_doubles.double_foot_lock import FootLockControllerDouble
        return FootLockControllerDouble

def get_ledge_physics_class():
    try:
        mod = importlib.import_module("src.visual.ledge_physics")
        return getattr(mod, "LedgePhysics")
    except Exception:
        from tests.test_doubles.double_ledge_physics import LedgePhysicsDouble
        return LedgePhysicsDouble

def get_procedural_motion_class():
    try:
        mod = importlib.import_module("src.visual.procedural_motion")
        return getattr(mod, "ProceduralMotion")
    except Exception:
        from tests.test_doubles.double_procedural_motion import ProceduralMotionDouble
        return ProceduralMotionDouble

def get_vision_services_class():
    try:
        mod = importlib.import_module("src.services.vision_connector")
        return getattr(mod, "VisionConnector")
    except Exception:
        from tests.test_doubles.double_vision_services import VisionServicesDouble
        return VisionServicesDouble
