import math
import numpy as np

class ProceduralMotionDouble:
    def __init__(self, omega=8.0):
        self.omega = float(omega)
        self.gaze_angle = 0.0
        self.gaze_vel = 0.0
        self.breath_phase = 0.0
        self.breath_freq = 0.28
        self.stress_level = 0.0
        self.eye_offset = np.array([0.0, 0.0], dtype=np.float64)

    def trigger_stress(self):
        self.stress_level = 1.0
        self.breath_freq = 0.65

    def update_breathing(self, dt):
        decay = math.exp(-dt / 4.5)
        self.stress_level *= decay
        self.breath_freq = 0.28 + self.stress_level * (0.65 - 0.28)
        self.breath_phase += 2.0 * math.pi * self.breath_freq * dt
        chest_deflection = 0.035 * math.sin(self.breath_phase)
        clavicle_elevation = 0.008 * math.sin(self.breath_phase - 0.2)
        return chest_deflection, clavicle_elevation

    def update_gaze_spring(self, target_angle_rad, dt):
        target_clamped = float(np.clip(target_angle_rad, -math.radians(85.0), math.radians(85.0)))
        k1 = self.omega * dt
        alpha = 1.0 / (1.0 + k1 + 0.48 * (k1**2) + 0.235 * (k1**3))
        new_angle = alpha * (self.gaze_angle + dt * self.gaze_vel + k1 * target_clamped)
        self.gaze_vel = alpha * (self.gaze_vel + k1 * (target_clamped - self.gaze_angle))
        self.gaze_angle = new_angle
        return self.gaze_angle

    def update_ocular_saccades(self, t):
        jitter_x = 0.008 * (math.sin(31.4 * t) + math.cos(71.2 * t))
        jitter_y = 0.008 * (math.cos(29.1 * t) + math.sin(68.5 * t))
        self.eye_offset[0] = jitter_x
        self.eye_offset[1] = jitter_y
        return float(jitter_x), float(jitter_y)
