from pathlib import Path

from PyQt5.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen, QPixmap, QRadialGradient
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class PointsBoardWidget(QWidget):
    intersection_clicked = pyqtSignal(int, int)

    def __init__(self, rows: int, cols: int):
        super().__init__()
        self.rows = rows
        self.cols = cols
        self.current_player_key = "J1"
        self.cell_size = 45
        self.cell_width = 45.0
        self.cell_height = 45.0
        self.margin = 30
        self.cannon_lane_width = 92
        self.intersection_radius = 5
        self.click_radius = 12
        self.board_left = self.margin
        self.board_top = self.margin
        self.points: dict[tuple[int, int], str] = {}
        self.traced_alignments: list[tuple[list[tuple[int, int]], str]] = []
        self.shot_marker: tuple[int, int, str] | None = None
        self.shot_animation_progress = 1.0
        self.shot_animation_active = False
        self.hit_effects: list[dict[str, float | str]] = []
        initial_row = self.rows // 2
        self.cannon_rows: dict[str, int] = {"J1": initial_row, "J2": initial_row}
        self.cannon_pixmaps = self._load_cannon_pixmaps()
        self.shot_animation_timer = QTimer(self)
        self.shot_animation_timer.setInterval(16)
        self.shot_animation_timer.timeout.connect(self._advance_shot_animation)
        self.hit_effect_timer = QTimer(self)
        self.hit_effect_timer.setInterval(16)
        self.hit_effect_timer.timeout.connect(self._advance_hit_effects)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(320, 240)

    def _load_cannon_pixmaps(self) -> dict[str, QPixmap]:
        assets_dir = Path(__file__).resolve().parent.parent / "assets"
        left = QPixmap(str(assets_dir / "cannon_left.svg"))
        right = QPixmap(str(assets_dir / "cannon_right.svg"))
        return {"J1": left, "J2": right}

    def _advance_shot_animation(self) -> None:
        if not self.shot_animation_active:
            return

        self.shot_animation_progress = min(1.0, self.shot_animation_progress + 0.06)
        if self.shot_animation_progress >= 1.0:
            self.shot_animation_active = False
            self.shot_animation_timer.stop()

        self.update()

    def _advance_hit_effects(self) -> None:
        if not self.hit_effects:
            self.hit_effect_timer.stop()
            return

        updated_effects: list[dict[str, float | str]] = []
        for effect in self.hit_effects:
            progress = float(effect["progress"]) + 0.10
            if progress < 1.0:
                effect["progress"] = progress
                updated_effects.append(effect)

        self.hit_effects = updated_effects
        if not self.hit_effects:
            self.hit_effect_timer.stop()

        self.update()

    def _start_hit_effect(self, row: int, col: int, owner: str) -> None:
        self.hit_effects.append({"row": float(row), "col": float(col), "owner": owner, "progress": 0.0})
        if not self.hit_effect_timer.isActive():
            self.hit_effect_timer.start()

    def _recalculate_metrics(self) -> None:
        width = max(1, self.width())
        height = max(1, self.height())

        base_cell_width = width / self.cols
        base_cell_height = height / self.rows
        base_cell_size = max(1.0, min(base_cell_width, base_cell_height))
        self.cannon_lane_width = max(40.0, min(78.0, base_cell_size * 1.8))

        self.intersection_radius = 2 if base_cell_size <= 4 else 3

        edge_padding = self.intersection_radius + 2
        horizontal_padding = edge_padding + self.cannon_lane_width
        drawable_width = max(1, width - 2 * horizontal_padding)
        drawable_height = max(1, height - 2 * edge_padding)

        self.cell_size = max(1.0, min(drawable_width / self.cols, drawable_height / self.rows))
        self.cell_width = self.cell_size
        self.cell_height = self.cell_size

        board_width = self.cols * self.cell_width
        board_height = self.rows * self.cell_height
        self.board_left = (width - board_width) / 2.0
        self.board_top = (height - board_height) / 2.0

        self.click_radius = max(8, min(18, int(self.cell_size * 0.38 + 6)))

    def set_points(self, points: dict[tuple[int, int], str]) -> None:
        previous_points = self.points
        removed_points = [
            (row, col, owner)
            for (row, col), owner in previous_points.items()
            if (row, col) not in points
        ]
        self.points = dict(points)
        for row, col, owner in removed_points:
            self._start_hit_effect(row, col, owner)
        self.update()

    def set_traced_alignments(self, alignments: list[tuple[list[tuple[int, int]], str]]) -> None:
        self.traced_alignments = [(list(coords), player) for coords, player in alignments]
        self.update()

    def set_shot_marker(self, marker: tuple[int, int, str] | None) -> None:
        self.shot_marker = marker
        if marker is None:
            self.shot_animation_active = False
            self.shot_animation_progress = 1.0
            self.shot_animation_timer.stop()
        else:
            self.shot_animation_progress = 0.0
            self.shot_animation_active = True
            self.shot_animation_timer.start()
        self.update()

    def set_current_player(self, player_key: str) -> None:
        if player_key in self.cannon_rows:
            self.current_player_key = player_key
            self.update()

    def move_cannon(self, player_key: str, delta: int) -> bool:
        if player_key not in self.cannon_rows or delta == 0:
            return False

        current_row = self.cannon_rows[player_key]
        target_row = max(0, min(self.rows, current_row + delta))
        if target_row == current_row:
            return False

        self.cannon_rows[player_key] = target_row
        self.update()
        return True

    def set_cannon_rows(self, cannon_rows: dict[str, int]) -> None:
        self.cannon_rows = {
            "J1": max(0, min(self.rows, cannon_rows.get("J1", self.rows // 2))),
            "J2": max(0, min(self.rows, cannon_rows.get("J2", self.rows // 2))),
        }
        self.update()

    def _to_pixel(self, row: int, col: int) -> tuple[float, float]:
        x = self.board_left + col * self.cell_width
        y = self.board_top + row * self.cell_height
        return x, y

    def paintEvent(self, event):
        self._recalculate_metrics()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        self._draw_battlefield_background(painter)

        board_rect = QRectF(
            self.board_left,
            self.board_top,
            self.cols * self.cell_width,
            self.rows * self.cell_height,
        )
        panel_gradient = QLinearGradient(board_rect.left(), board_rect.top(), board_rect.left(), board_rect.bottom())
        panel_gradient.setColorAt(0.0, QColor("#f6e39a"))
        panel_gradient.setColorAt(1.0, QColor("#e3c26f"))
        painter.setBrush(QBrush(panel_gradient))
        painter.setPen(QPen(QColor("#fff7d7"), 2))
        painter.drawRoundedRect(board_rect, 12, 12)

        line_pen = QPen(QColor("#8d6a3c"), 1)
        painter.setPen(line_pen)

        for row in range(self.rows + 1):
            y = self.board_top + row * self.cell_height
            x1 = self.board_left
            x2 = self.board_left + self.cols * self.cell_width
            painter.drawLine(int(x1), int(y), int(x2), int(y))

        for col in range(self.cols + 1):
            x = self.board_left + col * self.cell_width
            y1 = self.board_top
            y2 = self.board_top + self.rows * self.cell_height
            painter.drawLine(int(x), int(y1), int(x), int(y2))

        self._draw_cannons(painter)

        for coords, player in self.traced_alignments:
            if len(coords) < 2:
                continue

            trace_color = QColor("#9b6bff") if player == "J1" else QColor("#ff9c4d")
            trace_pen = QPen(trace_color, 3)
            painter.setPen(trace_pen)

            for idx in range(len(coords) - 1):
                r1, c1 = coords[idx]
                r2, c2 = coords[idx + 1]
                x1, y1 = self._to_pixel(r1, c1)
                x2, y2 = self._to_pixel(r2, c2)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        painter.setPen(Qt.NoPen)
        radius = self.intersection_radius + 1
        for (row, col), player in self.points.items():
            center_x = self.board_left + col * self.cell_width
            center_y = self.board_top + row * self.cell_height

            glow = QRadialGradient(center_x, center_y, radius * 3)
            if player == "J1":
                glow.setColorAt(0.0, QColor("#dcc9ff"))
                glow.setColorAt(0.5, QColor("#9b6bff"))
                glow.setColorAt(1.0, QColor(155, 107, 255, 0))
            else:
                glow.setColorAt(0.0, QColor("#ffe4bd"))
                glow.setColorAt(0.5, QColor("#ff9c4d"))
                glow.setColorAt(1.0, QColor(255, 156, 77, 0))
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(int(center_x - radius * 2), int(center_y - radius * 2), radius * 4, radius * 4)

            core_color = QColor("#9b6bff") if player == "J1" else QColor("#ff9c4d")
            painter.setBrush(QBrush(core_color))
            painter.drawEllipse(int(center_x - radius), int(center_y - radius), radius * 2, radius * 2)

        self._draw_hit_effects(painter)

        if self.shot_marker is not None:
            marker_row, marker_col, marker_color = self.shot_marker
            marker_x, marker_y = self._to_pixel(marker_row, marker_col)
            self._draw_shot_animation(painter, marker_row, marker_col)
            color = QColor("#2e7d32") if marker_color == "green" else QColor("#d32f2f")
            marker_pen = QPen(color, 2)
            painter.setPen(marker_pen)
            painter.setBrush(Qt.NoBrush)
            marker_radius = max(radius + 3, 6)
            painter.drawEllipse(
                int(marker_x - marker_radius),
                int(marker_y - marker_radius),
                marker_radius * 2,
                marker_radius * 2,
            )

    def _draw_battlefield_background(self, painter: QPainter) -> None:
        sky_gradient = QLinearGradient(0, 0, 0, self.height())
        sky_gradient.setColorAt(0.0, QColor("#ffd27a"))
        sky_gradient.setColorAt(0.52, QColor("#ffc07c"))
        sky_gradient.setColorAt(1.0, QColor("#8fd96e"))
        painter.setBrush(QBrush(sky_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

    def _draw_hit_effects(self, painter: QPainter) -> None:
        if not self.hit_effects:
            return

        painter.setPen(Qt.NoPen)
        for effect in self.hit_effects:
            row = int(effect["row"])
            col = int(effect["col"])
            progress = float(effect["progress"])
            owner = str(effect["owner"])
            center_x, center_y = self._to_pixel(row, col)

            if owner == "J1":
                burst_color = QColor("#9b6bff")
            else:
                burst_color = QColor("#ff9c4d")

            ring_radius = max(4.0, self.cell_size * (0.14 + 0.42 * progress))
            ring_pen = QPen(QColor(burst_color.red(), burst_color.green(), burst_color.blue(), int(220 * (1.0 - progress))), 2)
            painter.setPen(ring_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(
                int(center_x - ring_radius),
                int(center_y - ring_radius),
                int(ring_radius * 2),
                int(ring_radius * 2),
            )

            painter.setPen(Qt.NoPen)
            burst = QRadialGradient(center_x, center_y, max(6.0, self.cell_size * 0.45))
            burst.setColorAt(0.0, QColor(255, 245, 190, int(230 * (1.0 - progress))))
            burst.setColorAt(0.4, QColor(burst_color.red(), burst_color.green(), burst_color.blue(), int(180 * (1.0 - progress))))
            burst.setColorAt(1.0, QColor(burst_color.red(), burst_color.green(), burst_color.blue(), 0))
            painter.setBrush(QBrush(burst))
            splash_radius = max(5, int(self.cell_size * (0.12 + 0.28 * progress)))
            painter.drawEllipse(
                int(center_x - splash_radius),
                int(center_y - splash_radius),
                splash_radius * 2,
                splash_radius * 2,
            )

    def _draw_shot_animation(self, painter: QPainter, marker_row: int, marker_col: int) -> None:
        if not self.shot_animation_active and self.shot_animation_progress >= 1.0:
            return

        board_right = self.board_left + self.cols * self.cell_width
        shooter_row = self.cannon_rows.get(self.current_player_key, self.rows // 2)
        _, shooter_y = self._to_pixel(shooter_row, 0)
        target_x, target_y = self._to_pixel(marker_row, marker_col)

        if self.current_player_key == "J1":
            shooter_x = self.board_left - self.cannon_lane_width * 0.2
        else:
            shooter_x = board_right + self.cannon_lane_width * 0.2

        t = self.shot_animation_progress
        base_x = shooter_x + (target_x - shooter_x) * t
        base_y = shooter_y + (target_y - shooter_y) * t

        arc_height = max(80.0, self.cell_size * 4.2)
        lift = 4 * arc_height * t * (1 - t)
        iso_direction = 1.0 if self.current_player_key == "J1" else -1.0
        iso_x_offset = iso_direction * lift * 0.52
        iso_y_offset = lift * 0.70

        current_x = base_x + iso_x_offset
        current_y = base_y - iso_y_offset

        painter.setPen(Qt.NoPen)

        shadow_width = max(10, int(self.cell_size * 0.48))
        shadow_height = max(4, int(shadow_width * 0.35))
        shadow_alpha = max(45, int(130 * (1.0 - (lift / arc_height))))
        painter.setBrush(QBrush(QColor(20, 20, 20, shadow_alpha)))
        painter.drawEllipse(
            int(base_x - shadow_width),
            int(base_y - shadow_height * 0.5),
            shadow_width * 2,
            shadow_height,
        )

        trail = QRadialGradient(current_x, current_y, max(8.0, self.cell_size * 0.45))
        trail.setColorAt(0.0, QColor("#fff8d7"))
        trail.setColorAt(0.55, QColor("#ffd268"))
        trail.setColorAt(1.0, QColor(255, 169, 64, 0))
        painter.setBrush(QBrush(trail))
        trail_radius = max(8, int(self.cell_size * 0.45))
        painter.drawEllipse(int(current_x - trail_radius), int(current_y - trail_radius), trail_radius * 2, trail_radius * 2)

        painter.setBrush(QBrush(QColor("#2a2a2a")))
        ball_radius = max(4, int(self.cell_size * 0.15))
        painter.drawEllipse(int(current_x - ball_radius), int(current_y - ball_radius), ball_radius * 2, ball_radius * 2)

        painter.setBrush(QBrush(QColor(255, 255, 255, 170)))
        shine = max(2, int(ball_radius * 0.45))
        painter.drawEllipse(int(current_x - ball_radius * 0.4), int(current_y - ball_radius * 0.6), shine, shine)

    def _draw_cannons(self, painter: QPainter) -> None:
        board_right = self.board_left + self.cols * self.cell_width

        for player_key, row in self.cannon_rows.items():
            _, y = self._to_pixel(row, 0)
            is_left = player_key == "J1"
            is_current = self.current_player_key == player_key
            cannon_height = max(22.0, min(42.0, self.cell_size * 1.35))
            cannon_width = cannon_height * 1.65

            if is_left:
                cannon_x = self.board_left - self.cannon_lane_width + (self.cannon_lane_width - cannon_width) * 0.5
            else:
                cannon_x = board_right + (self.cannon_lane_width - cannon_width) * 0.5

            cannon_x = max(2.0, min(cannon_x, self.width() - cannon_width - 2.0))

            cannon_rect = QRectF(cannon_x, y - cannon_height * 0.6, cannon_width, cannon_height)

            if is_current:
                glow = QRadialGradient(cannon_rect.center(), cannon_width * 0.75)
                glow.setColorAt(0.0, QColor(255, 209, 102, 120))
                glow.setColorAt(1.0, QColor(255, 209, 102, 0))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(glow))
                painter.drawEllipse(cannon_rect.adjusted(-8, -8, 8, 8))

            pixmap = self.cannon_pixmaps.get(player_key)
            if pixmap is not None and not pixmap.isNull():
                painter.drawPixmap(cannon_rect.toRect(), pixmap)
                continue

            color = QColor("#8fa5b8")
            body_pen = QPen(color, 3 if is_current else 2)
            painter.setPen(body_pen)
            painter.setBrush(QBrush(color))

            if is_left:
                base_x = self.board_left - self.cannon_lane_width
                barrel_start = base_x
                barrel_end = self.board_left - 3
                body_center_x = base_x - 8
                tip = QPointF(barrel_end + 2, y)
                base_top = QPointF(barrel_end - 8, y - 6)
                base_bottom = QPointF(barrel_end - 8, y + 6)
            else:
                base_x = board_right + self.cannon_lane_width
                barrel_start = board_right + 3
                barrel_end = base_x
                body_center_x = base_x + 8
                tip = QPointF(barrel_start - 2, y)
                base_top = QPointF(barrel_start + 8, y - 6)
                base_bottom = QPointF(barrel_start + 8, y + 6)

            painter.drawLine(int(barrel_start), int(y), int(barrel_end), int(y))
            painter.drawEllipse(int(body_center_x - 5), int(y - 5), 10, 10)
            painter.drawPolygon([tip, base_top, base_bottom])

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        nearest = self._nearest_intersection(event.x(), event.y())
        if nearest is None:
            return

        row, col = nearest
        self.intersection_clicked.emit(row, col)

    def _nearest_intersection(self, x: int, y: int):
        self._recalculate_metrics()

        if self.cell_width <= 0 or self.cell_height <= 0:
            return None

        board_right = self.board_left + self.cols * self.cell_width
        board_bottom = self.board_top + self.rows * self.cell_height
        outside_margin = max(self.click_radius, int(self.cell_size * 0.5))
        if (
            x < self.board_left - outside_margin
            or x > board_right + outside_margin
            or y < self.board_top - outside_margin
            or y > board_bottom + outside_margin
        ):
            return None

        raw_col = (x - self.board_left) / self.cell_width
        raw_row = (y - self.board_top) / self.cell_height
        nearest_col = max(0, min(self.cols, int(round(raw_col))))
        nearest_row = max(0, min(self.rows, int(round(raw_row))))

        ix = self.board_left + nearest_col * self.cell_width
        iy = self.board_top + nearest_row * self.cell_height
        dx = ix - x
        dy = iy - y
        distance_sq = dx * dx + dy * dy

        extended_click_radius = max(self.click_radius + 3, int(self.cell_size * 0.95))
        if distance_sq <= extended_click_radius * extended_click_radius:
            return (nearest_row, nearest_col)

        return None


class GridWindow(QWidget):
    shot_power_selected = pyqtSignal(int)
    end_game_requested = pyqtSignal()
    save_game_requested = pyqtSignal()
    load_game_requested = pyqtSignal()

    def __init__(self, rows: int, cols: int):
        super().__init__()
        self.setWindowTitle("Jeu de points")
        self.current_player_key = "J1"
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #2f2440;
                color: #fff6da;
                font-size: 14px;
            }
            QLabel {
                color: #fff6da;
                font-weight: 600;
                padding: 4px 8px;
            }
            QPushButton {
                background-color: #f2c14e;
                color: #3d2c13;
                border: 1px solid #ffebad;
                border-radius: 10px;
                padding: 8px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #ffd770;
            }
            QPushButton:pressed {
                background-color: #ddad3a;
            }
            """
        )

        screen = QApplication.primaryScreen()
        if screen is not None:
            geometry = screen.geometry()
            window_width = geometry.width()
            window_height = geometry.height()
        else:
            window_width = 1280
            window_height = 720

        self.board = PointsBoardWidget(rows, cols)
        self.board.set_current_player(self.current_player_key)
        self.board_container = QWidget()
        self.board_container.setStyleSheet("background: transparent;")
        self.controls_enabled = False
        self.turn_label = QLabel("Tour actuel : J1")
        self.turn_label.setAlignment(Qt.AlignCenter)
        self.score_label = QLabel("Score - Joueur 1: 0 | Joueur 2: 0")
        self.score_label.setAlignment(Qt.AlignCenter)
        self.next_player_banner = QLabel("")
        self.next_player_banner.setAlignment(Qt.AlignCenter)
        self.next_player_banner.setParent(self)
        self.next_player_banner.setVisible(False)
        self.next_player_banner.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.next_player_banner.setStyleSheet(
            "color: #ffd15f; font-size: 52px; font-weight: 900; "
            "background: transparent; padding: 4px 10px;"
        )
        self.banner_opacity_effect = QGraphicsOpacityEffect(self.next_player_banner)
        self.banner_opacity_effect.setOpacity(1.0)
        self.next_player_banner.setGraphicsEffect(self.banner_opacity_effect)
        self.banner_fade_animation = QPropertyAnimation(self.banner_opacity_effect, b"opacity", self)
        self.banner_fade_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.banner_fade_animation.finished.connect(self._hide_next_player_banner)
        self.instructions_label = QLabel(
            "Commandes\n"
            "- Déplacer le canon : Haut / Bas\n"
            "- Viser/Tirer : Ctrl + 0 à Ctrl + 9\n"
            "- Placer un point : clic gauche sur une intersection\n"
            "Chaque tour : un seul coup (tir validé ou placement)."
        )
        self.instructions_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.instructions_label.setWordWrap(True)
        self.instructions_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.instructions_label.setFixedWidth(250)
        self.instructions_label.setStyleSheet(
            "color: #2f2440; background-color: #ffe6a6; border: 2px solid #f2c14e; "
            "border-radius: 12px; padding: 10px 14px; font-size: 13px;"
        )
        self.save_game_button = QPushButton("Enregistrer partie")
        self.save_game_button.clicked.connect(self.save_game_requested.emit)
        self.load_game_button = QPushButton("Charger partie")
        self.load_game_button.clicked.connect(self.load_game_requested.emit)
        self.end_game_button = QPushButton("Fin de partie")
        self.end_game_button.clicked.connect(self.end_game_requested.emit)

        board_container_layout = QVBoxLayout(self.board_container)
        board_container_layout.setContentsMargins(0, 0, 0, 0)
        board_container_layout.addWidget(self.board)

        self.resize(window_width, window_height)
        self._update_container_size()

        root_layout = QVBoxLayout(self)
        root_layout.addWidget(self.turn_label)
        root_layout.addWidget(self.score_label)
        root_layout.addStretch()

        center_row = QHBoxLayout()
        center_row.addWidget(self.instructions_label)
        center_row.addSpacing(14)
        center_row.addStretch()
        center_row.addWidget(self.board_container)
        center_row.addStretch()

        actions_row = QHBoxLayout()
        actions_row.addStretch()
        actions_row.addWidget(self.save_game_button)
        actions_row.addSpacing(12)
        actions_row.addWidget(self.load_game_button)
        actions_row.addSpacing(12)
        actions_row.addWidget(self.end_game_button)
        actions_row.addStretch()

        root_layout.addLayout(center_row)
        root_layout.addLayout(actions_row)
        root_layout.addStretch()
        self.setFocus()

    def set_current_player(self, player: str):
        self.turn_label.setText(f"Tour actuel : {player}")

    def set_current_player_key(self, player_key: str):
        self.current_player_key = player_key
        self.board.set_current_player(player_key)

    def set_scores(self, j1_name: str, j1_score: int, j2_name: str, j2_score: int):
        self.score_label.setText(f"Score - {j1_name}: {j1_score} | {j2_name}: {j2_score}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_container_size()
        self._reposition_next_player_banner()

    def keyPressEvent(self, event):
        if not self.controls_enabled:
            super().keyPressEvent(event)
            return

        modifiers = event.modifiers()
        if event.key() == Qt.Key_Up:
            if self.board.move_cannon(self.current_player_key, -1):
                return
        elif event.key() == Qt.Key_Down:
            if self.board.move_cannon(self.current_player_key, 1):
                return
        elif modifiers & Qt.ControlModifier and Qt.Key_0 <= event.key() <= Qt.Key_9:
            power = (event.key() - Qt.Key_0) + 1
            self.shot_power_selected.emit(power)
            return

        super().keyPressEvent(event)

    def set_controls_enabled(self, enabled: bool):
        self.controls_enabled = enabled

    def show_next_player_banner(self, player_name: str, player_key: str, duration_ms: int = 1300):
        self.banner_fade_animation.stop()
        banner_color = "#5aa8ff" if player_key == "J1" else "#ff5f5f"
        self.next_player_banner.setStyleSheet(
            f"color: {banner_color}; font-size: 52px; font-weight: 900; "
            "background: transparent; padding: 4px 10px;"
        )
        self.next_player_banner.setText(f"Tour de {player_name}")
        self.next_player_banner.adjustSize()
        self._reposition_next_player_banner()
        self.banner_opacity_effect.setOpacity(1.0)
        self.next_player_banner.setVisible(True)
        self.banner_fade_animation.setDuration(max(900, duration_ms))
        self.banner_fade_animation.setStartValue(1.0)
        self.banner_fade_animation.setEndValue(0.0)
        self.banner_fade_animation.start()

    def _hide_next_player_banner(self):
        self.next_player_banner.setVisible(False)
        self.banner_opacity_effect.setOpacity(1.0)

    def _reposition_next_player_banner(self):
        self.next_player_banner.adjustSize()
        x = max(0, (self.width() - self.next_player_banner.width()) // 2)
        y = max(0, (self.height() - self.next_player_banner.height()) // 2)
        self.next_player_banner.move(x, y)
        self.next_player_banner.raise_()

    def _update_container_size(self):
        horizontal_padding = 80
        vertical_padding = 230
        instructions_block = self.instructions_label.width() + 20
        available_width = max(280, self.width() - horizontal_padding - instructions_block)
        available_height = max(220, self.height() - vertical_padding)

        container_width = min(max(320, int(self.width() * 0.74)), available_width)
        container_height = min(max(240, int(self.height() * 0.66)), available_height)
        self.board_container.setFixedSize(container_width, container_height)
