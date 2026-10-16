from typing import Optional
from PyQt6.QtCore import Qt, QRect, QRectF, QPoint
from PyQt6.QtGui import (
    QPainter, QPainterPath, QLinearGradient, QColor,
    QPen, QFont, QFontMetrics, QPixmap, QRegion
)
from PyQt6.QtWidgets import QApplication

class BalloonRenderer:
    @staticmethod
    def recalculate_responsive_layout(overlay):
        ov = overlay
        if getattr(ov, "using_vrm", False):
            avatar_w = getattr(ov, "avatar_width", 330)
            avatar_h = getattr(ov, "avatar_height", 550)
            head_y_in_avatar = int(avatar_h * 0.28)
        elif getattr(ov, "using_live2d", True):
            avatar_w = getattr(ov, "avatar_width", 260)
            avatar_h = getattr(ov, "avatar_height", 360)
            head_y_in_avatar = 80
        else:
            avatar_w = 180
            avatar_h = 180
            head_y_in_avatar = 50

        if not ov.balloon_text:
            new_w = avatar_w + 20
            new_h = avatar_h + 16
            ov.combined_balloon_path = QPainterPath()
            ov.bubble_rect = QRectF()
            vy = 8
        else:
            balloon_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            fm = QFontMetrics(balloon_font)

            text_len = len(ov.balloon_text)
            if text_len < 25:
                wrap_w = 190
            elif text_len < 60:
                wrap_w = 250
            elif text_len < 120:
                wrap_w = 300
            elif text_len < 200:
                wrap_w = 330
            else:
                wrap_w = 350

            bounding = fm.boundingRect(QRect(0, 0, wrap_w, 800), Qt.TextFlag.TextWordWrap, ov.balloon_text)
            text_w = max(bounding.width(), 85)
            text_h = max(bounding.height(), 18)

            bw = min(max(text_w + 52, 160), 390)
            bh = max(text_h + 24, 42)
            tail_h = 10

            by = 10.0
            tail_tip_y = by + bh + tail_h
            vy = int(tail_tip_y + 14)

            new_w = max(int(bw) + 28, avatar_w + 30)
            new_h = vy + avatar_h + 10

            bx = max(12.0, float((new_w - bw) / 2.0))
            ov.bubble_rect = QRectF(bx, by, bw, bh)

            head_center_x = float(new_w / 2.0)
            tail_cx = min(max(bx + 28.0, head_center_x), bx + bw - 28.0)
            tail_top_y = by + bh
            tail_tip_y = by + bh + tail_h

            tail_path = QPainterPath()
            tail_path.moveTo(tail_cx - 8, tail_top_y - 1)
            tail_path.lineTo(tail_cx, tail_tip_y)
            tail_path.lineTo(tail_cx + 8, tail_top_y - 1)
            tail_path.closeSubpath()

            bubble_path = QPainterPath()
            bubble_path.addRoundedRect(ov.bubble_rect, 14, 14)

            ov.combined_balloon_path = bubble_path.united(tail_path)

        screens = QApplication.screens()
        screen_geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1200)
        sw = screen_geom.width()
        sh = screen_geom.height()

        margin_left = 20
        margin_top = 70
        margin_right = 35
        margin_bottom = 35

        if not hasattr(ov, "anchor_bottom_right") or ov.anchor_bottom_right.isNull():
            ov.anchor_bottom_right = QPoint(sw - margin_right, sh - margin_bottom)

        br_x = ov.anchor_bottom_right.x()
        br_y = ov.anchor_bottom_right.y()

        if br_x > sw - margin_right:
            br_x = sw - margin_right
        if br_y > sh - margin_bottom:
            br_y = sh - margin_bottom

        new_x = br_x - new_w
        new_y = br_y - new_h

        if new_x < margin_left:
            new_x = margin_left
            br_x = new_x + new_w
        if new_y < margin_top:
            new_y = margin_top
            br_y = new_y + new_h

        if new_x + new_w > sw - margin_right:
            new_x = sw - margin_right - new_w
        if new_y + new_h > sh - margin_bottom:
            new_y = sh - margin_bottom - new_h

        ov.anchor_bottom_right = QPoint(int(new_x + new_w), int(new_y + new_h))

        ov.setGeometry(int(new_x), int(new_y), int(new_w), int(new_h))
        ov.sync_hyprland_position(int(new_x), int(new_y))

        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
            vx = max(0, (new_w - avatar_w) // 2)
            ov.vrm_widget.setGeometry(vx, vy, avatar_w, avatar_h)
            ov.vrm_widget.show()
            ov.vrm_widget.raise_()
            if hasattr(ov, "live2d_widget"):
                ov.live2d_widget.hide()
        elif getattr(ov, "using_live2d", True) and hasattr(ov, "live2d_widget"):
            lx = max(0, (new_w - avatar_w) // 2)
            ov.live2d_widget.setGeometry(lx, vy, avatar_w, avatar_h)
            ov.live2d_widget.show()
            if hasattr(ov, "vrm_widget"):
                ov.vrm_widget.hide()
        else:
            if hasattr(ov, "live2d_widget"):
                ov.live2d_widget.hide()
            if hasattr(ov, "vrm_widget"):
                ov.vrm_widget.hide()

        ov.clearMask()

    @staticmethod
    def render_overlay(overlay, painter: QPainter):
        ov = overlay
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(ov.rect(), Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setOpacity(ov.current_alpha)

        if not getattr(ov, "using_live2d", False) and not getattr(ov, "using_vrm", False) and ov.current_pixmap:
            sprite_w = ov.current_pixmap.width()
            sprite_h = ov.current_pixmap.height()
            x = ov.width() - sprite_w - 5
            y = ov.height() - sprite_h - 4
            painter.drawPixmap(x, y, ov.current_pixmap)

        if ov.balloon_text and hasattr(ov, "combined_balloon_path") and not ov.combined_balloon_path.isEmpty():
            painter.setOpacity(1.0)

            grad = QLinearGradient(0, ov.bubble_rect.top(), 0, ov.bubble_rect.bottom() + 10)
            grad.setColorAt(0.0, QColor(255, 105, 155, 242))
            grad.setColorAt(0.5, QColor(245, 80, 140, 245))
            grad.setColorAt(1.0, QColor(230, 55, 120, 246))

            painter.setPen(QPen(QColor(150, 20, 65, 80), 4.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(ov.combined_balloon_path)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad)
            painter.drawPath(ov.combined_balloon_path)

            glow_color = QColor(255, 120, 175, 75)
            painter.setPen(QPen(glow_color, 3.2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(ov.combined_balloon_path)

            border_color = QColor(255, 225, 242, 245)
            painter.setPen(QPen(border_color, 1.6))
            painter.drawPath(ov.combined_balloon_path)

            top_line_y = ov.bubble_rect.top() + 3.0
            left_x = ov.bubble_rect.left() + 20.0
            right_x = ov.bubble_rect.right() - 20.0
            if right_x > left_x:
                line_grad = QLinearGradient(left_x, top_line_y, right_x, top_line_y)
                line_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
                line_grad.setColorAt(0.5, QColor(255, 255, 255, 190))
                line_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
                painter.setPen(QPen(line_grad, 1.2))
                painter.drawLine(int(left_x), int(top_line_y), int(right_x), int(top_line_y))

            emoji_font = QFont("Segoe UI Emoji", 9)
            painter.setFont(emoji_font)
            painter.setPen(QColor(255, 255, 255, 220))

            bx = ov.bubble_rect.left()
            by = ov.bubble_rect.top()
            bw = ov.bubble_rect.width()
            bh = ov.bubble_rect.height()

            tl_rect = QRectF(bx + 7.0, by + 4.0, 16.0, 16.0)
            painter.drawText(tl_rect, Qt.AlignmentFlag.AlignCenter, "🌸")

            tr_rect = QRectF(bx + bw - 23.0, by + 4.0, 16.0, 16.0)
            painter.drawText(tr_rect, Qt.AlignmentFlag.AlignCenter, "✨")

            bl_rect = QRectF(bx + 7.0, by + bh - 20.0, 16.0, 16.0)
            painter.drawText(bl_rect, Qt.AlignmentFlag.AlignCenter, "🎀")

            br_rect = QRectF(bx + bw - 23.0, by + bh - 20.0, 16.0, 16.0)
            painter.drawText(br_rect, Qt.AlignmentFlag.AlignCenter, "💖")

            font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            painter.setFont(font)
            text_rect = ov.bubble_rect.adjusted(22, 6, -22, -6)

            painter.setPen(QColor(135, 15, 60, 160))
            shadow_rect = text_rect.translated(1.0, 1.0)
            painter.drawText(
                shadow_rect,
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                ov.balloon_text
            )

            painter.setPen(QColor(255, 255, 255))
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                ov.balloon_text
            )
