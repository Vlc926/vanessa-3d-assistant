from typing import Any
import numpy as np

class FootLockController:
    def __init__(self, l1: float = 0.42, l2: float = 0.40, hip_rest_y: float = 0.82) -> None:
        self.l1 = float(l1)
        self.l2 = float(l2)
        self.total_len = self.l1 + self.l2
        self.hip_rest_y = float(hip_rest_y)
        self.state = "STANCE"
        self.local_anchor = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        self.window_pos = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        self.hip_pos = np.array([0.0, float(hip_rest_y), 0.0], dtype=np.float64)

    def plant_foot(self, world_foot_pos: Any, window_world_pos: Any) -> None:
        self.window_pos = np.asarray(window_world_pos, dtype=np.float64)
        self.local_anchor = np.asarray(world_foot_pos, dtype=np.float64) - self.window_pos
        self.state = "STANCE"

    def get_world_foot_pos(self, current_window_pos: Any) -> np.ndarray:
        self.window_pos = np.asarray(current_window_pos, dtype=np.float64)
        return self.window_pos + self.local_anchor

    def update_hip_position(self, current_window_pos: Any, pelvis_x: float, dt: float = 1.0 / 60.0) -> np.ndarray:
        target_foot = self.get_world_foot_pos(current_window_pos)
        self.hip_pos[0] = float(pelvis_x)
        d_hip = float(np.linalg.norm(target_foot - self.hip_pos))
        target_hip_y = self.hip_rest_y
        if d_hip >= 0.85 * self.total_len:
            stretch_excess = d_hip - 0.85 * self.total_len
            target_hip_y -= min(0.35, stretch_excess * 0.8)
        blend = min(1.0, 12.0 * max(0.0, float(dt)))
        self.hip_pos[1] = (1.0 - blend) * self.hip_pos[1] + blend * target_hip_y
        return np.copy(self.hip_pos)

    def check_liftoff(self, current_window_pos: Any, step_distance_threshold: float = 0.50) -> bool:
        target_foot = self.get_world_foot_pos(current_window_pos)
        dist = float(abs(target_foot[0] - self.hip_pos[0]))
        if dist >= float(step_distance_threshold):
            self.state = "SWING"
            return True
        return False
