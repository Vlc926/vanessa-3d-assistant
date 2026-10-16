import numpy as np

class TwoBoneIKSolverDouble:
    def __init__(self, l1=0.42, l2=0.40):
        self.l1 = float(l1)
        self.l2 = float(l2)
        self.total_len = self.l1 + self.l2

    def solve(self, p_root, p_target, v_pole):
        p_root = np.asarray(p_root, dtype=np.float64)
        p_target = np.asarray(p_target, dtype=np.float64)
        v_pole = np.asarray(v_pole, dtype=np.float64)

        d_vec = p_target - p_root
        dist = np.linalg.norm(d_vec)
        if dist < 1e-6:
            return p_root, p_root, p_root

        max_reach = self.total_len * 0.9999
        min_reach = abs(self.l1 - self.l2) + 1e-4
        eff_dist = np.clip(dist, min_reach, max_reach)
        u_target = d_vec / dist

        cos_t1 = (self.l1**2 + eff_dist**2 - self.l2**2) / (2.0 * self.l1 * eff_dist)
        cos_t2 = (self.l1**2 + self.l2**2 - eff_dist**2) / (2.0 * self.l1 * self.l2)
        t1 = np.arccos(np.clip(cos_t1, -1.0, 1.0))

        w_pole = v_pole - p_root
        plane_normal = np.cross(u_target, w_pole)
        norm_plane = np.linalg.norm(plane_normal)
        if norm_plane < 1e-5:
            fallback = np.array([0.0, 0.0, 1.0], dtype=np.float64)
            plane_normal = np.cross(u_target, fallback)
            norm_plane = np.linalg.norm(plane_normal)
            if norm_plane < 1e-5:
                plane_normal = np.array([1.0, 0.0, 0.0], dtype=np.float64)
            else:
                plane_normal /= norm_plane
        else:
            plane_normal /= norm_plane

        k = plane_normal
        cos_a = np.cos(t1)
        sin_a = np.sin(t1)
        d_upper = u_target * cos_a + np.cross(k, u_target) * sin_a + k * np.dot(k, u_target) * (1.0 - cos_a)
        norm_upper = np.linalg.norm(d_upper)
        if norm_upper > 1e-7:
            d_upper = d_upper / norm_upper
        else:
            d_upper = u_target

        p_knee = p_root + self.l1 * d_upper
        d_lower = p_target - p_knee
        norm_lower = np.linalg.norm(d_lower)
        if norm_lower > 1e-6:
            p_ankle = p_knee + self.l2 * (d_lower / norm_lower)
        else:
            p_ankle = p_knee

        return p_root, p_knee, p_ankle
