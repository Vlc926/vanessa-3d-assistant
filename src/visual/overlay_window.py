from typing import List, Sequence, Tuple

try:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import Gtk, Gdk, GObject, GtkLayerShell
    import cairo
    HAS_GTK = True
except (ImportError, ValueError):
    HAS_GTK = False
    Gtk = None
    Gdk = None
    GObject = None
    GtkLayerShell = None
    cairo = None

class OverlayWindow:
    def __init__(self, layer: int = 3, width: int = 1920, height: int = 1200):
        self.layer = int(layer)
        self.width = int(width)
        self.height = int(height)
        self.click_through_enabled = True
        self.mesh_rectangles: List[Tuple[float, float, float, float]] = []
        self.background_rgba = (0.0, 0.0, 0.0, 0.0)
        self.is_real = False
        self.window = None
        self._gdk_window = None

        if HAS_GTK:
            try:
                initialized, _ = Gtk.init_check()
                if initialized:
                    self._init_gtk_window()
            except Exception:
                self.is_real = False

    def _init_gtk_window(self):
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_default_size(self.width, self.height)
        self.window.set_app_paintable(True)

        screen = self.window.get_screen()
        visual = screen.get_rgba_visual()
        if visual is not None:
            self.window.set_visual(visual)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"window { background-color: rgba(0, 0, 0, 0); }")
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        def _on_draw(widget, cr):
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.0)
            cr.set_operator(cairo.Operator.CLEAR)
            cr.paint()
            cr.set_operator(cairo.Operator.OVER)
            return False

        self.window.connect("draw", _on_draw)

        if GtkLayerShell and GtkLayerShell.is_supported():
            GtkLayerShell.init_for_window(self.window)
            GtkLayerShell.set_layer(self.window, self.layer)
            GtkLayerShell.set_namespace(self.window, "jarvis-overlay")
            for edge in (
                GtkLayerShell.Edge.TOP,
                GtkLayerShell.Edge.BOTTOM,
                GtkLayerShell.Edge.LEFT,
                GtkLayerShell.Edge.RIGHT,
            ):
                GtkLayerShell.set_anchor(self.window, edge, True)
                GtkLayerShell.set_margin(self.window, edge, 0)
            GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.NONE)
            GtkLayerShell.set_exclusive_zone(self.window, -1)

        self.window.realize()
        self._gdk_window = self.window.get_window()
        self.is_real = True
        self._apply_input_region()

    def set_layer(self, layer_num: int):
        self.layer = int(layer_num)
        if self.is_real and self.window and GtkLayerShell and GtkLayerShell.is_supported():
            GtkLayerShell.set_layer(self.window, self.layer)

    def set_click_through(self, enabled: bool):
        self.click_through_enabled = bool(enabled)
        if self.is_real:
            self._apply_input_region()

    def update_avatar_mesh_bounds(self, rects: Sequence[Tuple[float, float, float, float]]):
        self.mesh_rectangles = [
            (float(r[0]), float(r[1]), float(r[2]), float(r[3]))
            for r in rects
        ]
        if self.is_real:
            self._apply_input_region()

    def _apply_input_region(self):
        if not self.is_real or not self._gdk_window or cairo is None:
            return
        if not self.click_through_enabled:
            full_rect = cairo.RectangleInt(0, 0, self.width, self.height)
            reg = cairo.Region(full_rect)
        elif not self.mesh_rectangles:
            reg = cairo.Region()
        else:
            reg = cairo.Region()
            for (x, y, w, h) in self.mesh_rectangles:
                rx = int(x)
                ry = int(y)
                rw = max(1, int(w) + 1)
                rh = max(1, int(h) + 1)
                reg.union(cairo.RectangleInt(rx, ry, rw, rh))
        self._gdk_window.input_shape_combine_region(reg, 0, 0)

    def test_point_intercepts_click(self, px: float, py: float) -> bool:
        if self.click_through_enabled and not self.mesh_rectangles:
            return False
        for (x, y, w, h) in self.mesh_rectangles:
            if x <= px <= (x + w) and y <= py <= (y + h):
                return True
        return not self.click_through_enabled

    def poll_events(self):
        if self.is_real and Gtk:
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)

    def show(self):
        if self.is_real and self.window:
            self.window.show_all()

    def hide(self):
        if self.is_real and self.window:
            self.window.hide()

    def destroy(self):
        if self.is_real and self.window:
            self.window.destroy()
            self.window = None
            self._gdk_window = None
            self.is_real = False
