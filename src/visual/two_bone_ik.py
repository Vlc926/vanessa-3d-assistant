import math
from typing import Any, Tuple
import numpy as np
from src.visual.foot_lock import FootLockController

class TwoBoneIKSolver:
    def __init__(self, l1: float = 0.42, l2: float = 0.40) -> None:
        self.l1 = float(l1)
        self.l2 = float(l2)
        self.total_len = self.l1 + self.l2

    def solve(
        self,
        p_root: Any,
        p_target: Any,
        v_pole: Any,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        p_root_arr = np.asarray(p_root, dtype=np.float64)
        p_target_arr = np.asarray(p_target, dtype=np.float64)
        v_pole_arr = np.asarray(v_pole, dtype=np.float64)

        d_vec = p_target_arr - p_root_arr
        dist = float(np.linalg.norm(d_vec))
        if dist < 1e-6:
            return np.copy(p_root_arr), np.copy(p_root_arr), np.copy(p_root_arr)

        max_reach = self.total_len * 0.9999
        min_reach = abs(self.l1 - self.l2) + 1e-4
        eff_dist = float(np.clip(dist, min_reach, max_reach))
        u_target = d_vec / dist
        p_eff_target = p_root_arr + eff_dist * u_target

        cos_t1 = float(np.clip((self.l1**2 + eff_dist**2 - self.l2**2) / (2.0 * self.l1 * eff_dist), -1.0, 1.0))
        t1 = math.acos(cos_t1)

        w_pole = v_pole_arr - p_root_arr
        plane_normal = np.cross(u_target, w_pole)
        norm_plane = float(np.linalg.norm(plane_normal))
        if norm_plane < 1e-5:
            fallback = np.array([0.0, 0.0, 1.0], dtype=np.float64)
            plane_normal = np.cross(u_target, fallback)
            norm_plane = float(np.linalg.norm(plane_normal))
            if norm_plane < 1e-5:
                plane_normal = np.array([1.0, 0.0, 0.0], dtype=np.float64)
            else:
                plane_normal /= norm_plane
        else:
            plane_normal /= norm_plane

        k = plane_normal
        cos_a = math.cos(t1)
        sin_a = math.sin(t1)
        d_upper = u_target * cos_a + np.cross(k, u_target) * sin_a + k * float(np.dot(k, u_target)) * (1.0 - cos_a)
        norm_upper = float(np.linalg.norm(d_upper))
        if norm_upper > 1e-7:
            d_upper /= norm_upper
        else:
            d_upper = u_target

        p_knee = p_root_arr + self.l1 * d_upper
        d_lower = p_eff_target - p_knee
        norm_lower = float(np.linalg.norm(d_lower))
        if norm_lower > 1e-6:
            p_ankle = p_knee + self.l2 * (d_lower / norm_lower)
        else:
            p_ankle = p_knee

        return p_root_arr, p_knee, p_ankle

__all__ = ["TwoBoneIKSolver", "FootLockController"]
