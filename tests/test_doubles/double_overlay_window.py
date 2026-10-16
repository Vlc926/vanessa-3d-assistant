class OverlayWindowDouble:
    def __init__(self, layer=3, width=1920, height=1200):
        self.layer = layer
        self.width = width
        self.height = height
        self.click_through_enabled = True
        self.mesh_rectangles = []
        self.background_rgba = (0.0, 0.0, 0.0, 0.0)

    def set_layer(self, layer_num):
        self.layer = layer_num

    def set_click_through(self, enabled):
        self.click_through_enabled = enabled

    def update_avatar_mesh_bounds(self, rects):
        self.mesh_rectangles = list(rects)

    def test_point_intercepts_click(self, px, py):
        if self.click_through_enabled and not self.mesh_rectangles:
            return False
        for (x, y, w, h) in self.mesh_rectangles:
            if x <= px <= (x + w) and y <= py <= (y + h):
                return True
        return not self.click_through_enabled
