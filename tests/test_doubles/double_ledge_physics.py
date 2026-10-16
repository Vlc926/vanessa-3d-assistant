import numpy as np

class LedgePhysicsDouble:
    def __init__(self, gravity=-18.5, terminal_velocity=35.0, imbalance_duration=0.45):
        self.gravity = float(gravity)
        self.terminal_velocity = float(terminal_velocity)
        self.imbalance_duration = float(imbalance_duration)
        self.pos = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        self.vel = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        self.state = "GROUNDED"
        self.imbalance_timer = 0.0
        self.landing_impact_speed = 0.0
        self.crouch_timer = 0.0

    def check_support(self, platforms):
        for p in platforms:
            x_min = p.get("x_min", -1e9)
            x_max = p.get("x_max", 1e9)
            y_top = p.get("y_top", 0.0)
            if (x_min - 0.05) <= self.pos[0] <= (x_max + 0.05):
                if abs(self.pos[1] - y_top) < 0.03:
                    return p
        return None

    def step(self, dt, platforms):
        dt = float(dt)
        if self.state == "GROUNDED":
            sup = self.check_support(platforms)
            if not sup and self.pos[1] > 0.01:
                self.state = "IMBALANCE"
                self.imbalance_timer = self.imbalance_duration
            elif sup:
                self.pos[1] = sup["y_top"]
                self.vel[1] = 0.0

        elif self.state == "IMBALANCE":
            self.imbalance_timer -= dt
            sup = self.check_support(platforms)
            if sup:
                self.state = "GROUNDED"
                self.imbalance_timer = 0.0
                self.pos[1] = sup["y_top"]
                self.vel[1] = 0.0
            elif self.imbalance_timer <= 0.0:
                self.state = "FREE_FALL"

        elif self.state == "FREE_FALL":
            self.vel[1] += self.gravity * dt
            if self.vel[1] < -self.terminal_velocity:
                self.vel[1] = -self.terminal_velocity

            prev_y = self.pos[1]
            next_y = prev_y + self.vel[1] * dt
            self.pos[0] += self.vel[0] * dt

            collided = False
            target_landing_y = 0.0

            for p in platforms:
                x_min = p.get("x_min", -1e9)
                x_max = p.get("x_max", 1e9)
                y_top = p.get("y_top", 0.0)
                if x_min <= self.pos[0] <= x_max:
                    if prev_y >= y_top >= next_y:
                        target_landing_y = y_top
                        collided = True
                        break

            if not collided and next_y <= 0.0:
                target_landing_y = 0.0
                collided = True

            if collided:
                self.landing_impact_speed = abs(self.vel[1])
                self.pos[1] = target_landing_y
                self.vel[1] = 0.0
                if self.landing_impact_speed >= 8.0:
                    self.state = "LANDING"
                    self.crouch_timer = 0.35
                else:
                    self.state = "GROUNDED"
            else:
                self.pos[1] = next_y

        elif self.state == "LANDING":
            self.crouch_timer -= dt
            if self.crouch_timer <= 0.0:
                self.state = "GROUNDED"
