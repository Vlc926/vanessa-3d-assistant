class ActuatorDouble:
    def __init__(self, execute_real=False):
        self.execute_real = execute_real
        self.recorded_dispatches = []
        self.recorded_pointer_events = []

    def dispatch_hyprctl(self, command, args=""):
        full_cmd = f"{command} {args}".strip()
        self.recorded_dispatches.append({"cmd": command, "args": args, "full": full_cmd})
        return {"status": "ok", "executed": full_cmd}

    def push_window(self, address, delta_x, delta_y):
        args = f"{int(delta_x)} {int(delta_y)},address:{address}"
        return self.dispatch_hyprctl("movewindowpixel", args)

    def resize_window(self, address, delta_w, delta_h):
        args = f"{int(delta_w)} {int(delta_h)},address:{address}"
        return self.dispatch_hyprctl("resizewindowpixel", args)

    def inject_pointer_move(self, x, y, absolute=True):
        entry = {"action": "mousemove", "x": x, "y": y, "absolute": absolute}
        self.recorded_pointer_events.append(entry)
        return {"status": "ok", "event": entry}

    def inject_pointer_click(self, button_code=0xC0):
        entry = {"action": "click", "button": button_code}
        self.recorded_pointer_events.append(entry)
        return {"status": "ok", "event": entry}

    def compute_push_displacement(self, impulse_force, avatar_mass=1.0, friction=0.2):
        if avatar_mass <= 0:
            return 0.0
        accel = impulse_force / avatar_mass
        disp = max(0.0, accel * (1.0 - friction))
        return round(disp, 2)
