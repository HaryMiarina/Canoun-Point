from PyQt5.QtCore import QPoint, QTimer, Qt
from PyQt5.QtWidgets import QDialog, QInputDialog, QMessageBox

from db.mongo import load_game as load_game_from_db
from db.mongo import list_saved_games, save_game as save_game_to_db
from model.game_model import BoardModel, Dimensions
from view.dimension_view import DimensionWindow
from view.grid_view import GridWindow


class GameController:
    def __init__(self):
        self.dimension_window = DimensionWindow()
        self.grid_window = None
        self.board_model = None
        self.current_player = "J1"
        self.player_names = {"J1": "Joueur 1", "J2": "Joueur 2"}
        self.points_to_align = {"J1": 5, "J2": 5}
        self.player_scores = {"J1": 0, "J2": 0}
        self.current_turn_action: str | None = None
        self.game_over = False
        self.turn_ready = False
        self._turn_sequence = 0
        self.traced_alignments: list[tuple[list[tuple[int, int]], str]] = []
        self.alignment_keys: set[tuple[str, tuple[tuple[int, int], ...]]] = set()
        self.alignment_reuse_counts: dict[tuple[str, tuple[tuple[int, int], ...]], int] = {}

        self.dimension_window.dimensions_submitted.connect(self.start_game)
        self.dimension_window.load_game_requested.connect(self.on_load_game_requested)

    def show(self):
        self.dimension_window.show()

    def start_game(
        self,
        rows: int,
        cols: int,
        player1_name: str,
        player2_name: str,
        points_to_align_j1: int,
        points_to_align_j2: int,
        start_turn: bool = True,
    ):
        if self.grid_window is not None:
            self.grid_window.close()

        dimensions = Dimensions(rows=rows, cols=cols)
        self.board_model = BoardModel(dimensions=dimensions)
        self.current_player = "J1"
        self.game_over = False
        self.turn_ready = False
        self._turn_sequence = 0
        self.player_names = {"J1": player1_name, "J2": player2_name}
        self.points_to_align = {"J1": points_to_align_j1, "J2": points_to_align_j2}
        self.player_scores = {"J1": 0, "J2": 0}
        self.traced_alignments = []
        self.alignment_keys = set()
        self.alignment_reuse_counts = {}

        self.grid_window = GridWindow(rows, cols)
        self.grid_window.board.set_points(self.board_model.points)
        self.grid_window.set_current_player_key(self.current_player)
        self.grid_window.set_current_player(self.player_names[self.current_player])
        self.grid_window.set_scores(
            self.player_names["J1"],
            self.player_scores["J1"],
            self.player_names["J2"],
            self.player_scores["J2"],
        )
        self.grid_window.board.set_shot_marker(None)
        self.grid_window.board.intersection_clicked.connect(self.on_intersection_clicked)
        self.grid_window.shot_power_selected.connect(self.on_shot_power_selected)
        self.grid_window.end_game_requested.connect(self.on_end_game_requested)
        self.grid_window.save_game_requested.connect(self.on_save_game_requested)
        self.grid_window.load_game_requested.connect(self.on_load_game_requested)
        self.grid_window.show()

        self.dimension_window.close()
        if start_turn:
            self._start_turn()

    def on_save_game_requested(self):
        if self.grid_window is None or self.board_model is None or self.game_over:
            return

        default_name = "partie_sauvegardee"
        game_name, ok = QInputDialog.getText(
            self.grid_window,
            "Enregistrer partie",
            "Nom de la sauvegarde :",
            text=default_name,
        )
        if not ok:
            return

        game_name = game_name.strip()
        if not game_name:
            QMessageBox.warning(self.grid_window, "Enregistrer", "Nom de sauvegarde invalide.", QMessageBox.Ok)
            return

        payload = self._serialize_game_state()
        try:
            save_game_to_db(game_name, payload)
        except Exception as error:
            QMessageBox.warning(
                self.grid_window,
                "Enregistrer",
                f"Impossible d'enregistrer la partie: {error}",
                QMessageBox.Ok,
            )
            return

        QMessageBox.information(
            self.grid_window,
            "Enregistrer",
            f"Partie enregistrée sous '{game_name}'.",
            QMessageBox.Ok,
        )

    def on_load_game_requested(self):
        parent = self.grid_window if self.grid_window is not None else self.dimension_window

        try:
            saved_games = list_saved_games()
        except Exception as error:
            QMessageBox.warning(
                parent,
                "Charger partie",
                f"Impossible de récupérer les sauvegardes: {error}",
                QMessageBox.Ok,
            )
            return

        if not saved_games:
            QMessageBox.information(parent, "Charger partie", "Aucune sauvegarde trouvée.", QMessageBox.Ok)
            return

        labels = [f"{entry['name']} - {entry['updated_at']}" for entry in saved_games]

        input_dialog = QInputDialog(parent)
        input_dialog.setWindowTitle("Charger partie")
        input_dialog.setLabelText("Choisissez une sauvegarde :")
        input_dialog.setComboBoxItems(labels)
        input_dialog.setComboBoxEditable(False)
        input_dialog.setStyleSheet(
            "QInputDialog { color: black; }"
            "QLabel { color: black; }"
            "QComboBox { color: black; }"
            "QComboBox QAbstractItemView { color: black; }"
            "QLineEdit { color: black; }"
        )

        if input_dialog.exec_() != QDialog.Accepted:
            return

        selected_label = input_dialog.textValue()

        selected_index = labels.index(selected_label)
        game_name = saved_games[selected_index]["name"]

        try:
            saved_state = load_game_from_db(game_name)
        except Exception as error:
            QMessageBox.warning(
                parent,
                "Charger partie",
                f"Impossible de charger la sauvegarde: {error}",
                QMessageBox.Ok,
            )
            return

        if not saved_state:
            QMessageBox.warning(parent, "Charger partie", "Sauvegarde introuvable.", QMessageBox.Ok)
            return

        self._restore_game_state(saved_state)
        active_parent = self.grid_window if self.grid_window is not None else parent
        QMessageBox.information(active_parent, "Charger partie", f"Partie '{game_name}' chargée.", QMessageBox.Ok)

    def on_intersection_clicked(self, row: int, col: int):
        if self.game_over:
            return

        if not self.turn_ready or self.board_model is None or self.grid_window is None:
            return

        played_by = self.current_player
        placed = self.board_model.place_point(row, col, self.current_player)
        if not placed:
            return

        self.grid_window.board.set_points(self.board_model.points)
        self._process_alignment_and_score(played_by, row, col)
        self._end_turn()

    def on_shot_power_selected(self, power: int):
        if self.game_over:
            return

        if not self.turn_ready or self.board_model is None or self.grid_window is None:
            return

        target = self._find_shot_target(self.current_player, power)
        if target is None:
            return

        is_valid_target = self._is_valid_enemy_shot_target(self.current_player, target)
        marker_color = "green" if is_valid_target else "red"
        row, col = target
        self.grid_window.board.set_shot_marker((row, col, marker_color))

        should_shoot = self._prompt_shot_resolution(is_valid_target, target)
        if should_shoot:
            self._resolve_shot(self.current_player, target, is_valid_target)
            return

        self.grid_window.board.set_shot_marker(None)

    def _start_turn(self):
        if self.game_over:
            return

        if self.grid_window is None:
            return

        self.turn_ready = False
        self._turn_sequence += 1
        turn_sequence = self._turn_sequence
        self.grid_window.board.set_shot_marker(None)
        self.grid_window.set_current_player_key(self.current_player)
        self.grid_window.set_current_player(self.player_names[self.current_player])
        self.current_turn_action = None
        self.grid_window.set_controls_enabled(False)
        self.grid_window.show_next_player_banner(self.player_names[self.current_player], self.current_player, 1800)
        QTimer.singleShot(1800, lambda: self._activate_turn(turn_sequence))

    def _activate_turn(self, turn_sequence: int) -> None:
        if self.game_over or self.grid_window is None:
            return
        if turn_sequence != self._turn_sequence:
            return

        self.turn_ready = True
        self.grid_window.set_controls_enabled(True)

    def _find_shot_target(self, player: str, power: int) -> tuple[int, int] | None:
        if self.grid_window is None or self.board_model is None:
            return None

        row = self.grid_window.board.cannon_rows.get(player, 0)
        clamped_power = max(1, min(10, power))
        cols = self.board_model.dimensions.cols
        projected_col = ((clamped_power - 1) * cols) // 9

        if player == "J1":
            col = projected_col
        else:
            col = cols - projected_col

        if col < 0 or col > cols:
            return None

        return (row, col)

    def _prompt_shot_resolution(self, is_valid_target: bool, target: tuple[int, int]) -> bool:
        message_box = QMessageBox()
        message_box.setWindowTitle("Décision de tir")
        message_box.setIcon(QMessageBox.Question)
        message_box.setWindowModality(Qt.ApplicationModal)
        row, col = target
        coordinates_text = f"Coordonnées : ligne {int(row)} colonne {int(col)}"
        if is_valid_target:
            message_box.setText(f"Témoin vert : cible valide. {coordinates_text}")
        else:
            message_box.setText(f"Témoin rouge : cible invalide. {coordinates_text}")
        message_box.setStandardButtons(QMessageBox.NoButton)

        shoot_button = message_box.addButton("Tirer", QMessageBox.AcceptRole)
        skip_button = message_box.addButton("Ne pas tirer", QMessageBox.ActionRole)
        message_box.adjustSize()
        window_top_left = self.grid_window.mapToGlobal(QPoint(0, 0))

        def place_popup():
            message_box.move(window_top_left.x() + 16, window_top_left.y() + 16)

        QTimer.singleShot(0, place_popup)
        QTimer.singleShot(25, place_popup)
        message_box.exec_()

        if message_box.clickedButton() == skip_button:
            return False
        return message_box.clickedButton() == shoot_button

    def _resolve_shot(self, player: str, target: tuple[int, int], is_valid_target: bool) -> None:
        if self.board_model is None or self.grid_window is None:
            return

        row, col = target
        self.grid_window.board.set_shot_marker(None)

        if is_valid_target and self.board_model.remove_point(row, col):
            self.grid_window.board.set_points(self.board_model.points)
            QMessageBox.information(
                self.grid_window,
                "Tir réussi",
                "Le point adverse est supprimé.",
                QMessageBox.Ok,
            )
            self._end_turn()
            return

        QMessageBox.information(
            self.grid_window,
            "Tir manqué",
            "Aucun point adverse non aligné à cet endroit. Tour perdu.",
            QMessageBox.Ok,
        )
        self._end_turn()

    def _is_valid_enemy_shot_target(self, player: str, target: tuple[int, int]) -> bool:
        if self.board_model is None:
            return False

        opponent = "J2" if player == "J1" else "J1"
        target_owner = self.board_model.points.get(target)
        if target_owner != opponent:
            return False

        return not self._is_point_in_traced_alignment(opponent, target)

    def _is_point_in_traced_alignment(self, player: str, point: tuple[int, int]) -> bool:
        for traced_points, traced_player in self.traced_alignments:
            if traced_player != player:
                continue
            if point in traced_points:
                return True
        return False

    def _end_turn(self):
        if self.game_over:
            return

        self.turn_ready = False
        self.current_turn_action = None
        self.current_player = "J2" if self.current_player == "J1" else "J1"
        self._start_turn()

    def on_end_game_requested(self):
        if self.grid_window is None or self.game_over:
            return

        self.game_over = True
        self.current_turn_action = None

        score_j1 = self.player_scores["J1"]
        score_j2 = self.player_scores["J2"]
        if score_j1 > score_j2:
            result_text = f"Gagnant : {self.player_names['J1']}"
        elif score_j2 > score_j1:
            result_text = f"Gagnant : {self.player_names['J2']}"
        else:
            result_text = "Match nul"

        QMessageBox.information(
            self.grid_window,
            "Fin de partie",
            (
                f"{result_text}\n"
                f"Score final - {self.player_names['J1']}: {score_j1} | "
                f"{self.player_names['J2']}: {score_j2}"
            ),
            QMessageBox.Ok,
        )
        self.dimension_window.show()
        self.dimension_window.raise_()
        self.dimension_window.activateWindow()
        self.grid_window.close()
        self.grid_window = None

    def _serialize_game_state(self) -> dict:
        if self.board_model is None or self.grid_window is None:
            return {}

        points_payload = [
            {"row": row, "col": col, "player": player}
            for (row, col), player in self.board_model.points.items()
        ]
        traced_payload = [
            {"player": player, "points": [[row, col] for row, col in points]}
            for points, player in self.traced_alignments
        ]
        alignment_keys_payload = [
            {"player": player, "points": [[row, col] for row, col in points]}
            for player, points in self.alignment_keys
        ]
        alignment_reuse_payload = [
            {"player": player, "points": [[row, col] for row, col in points], "reuse_count": reuse_count}
            for (player, points), reuse_count in self.alignment_reuse_counts.items()
        ]

        return {
            "rows": self.board_model.dimensions.rows,
            "cols": self.board_model.dimensions.cols,
            "player_names": dict(self.player_names),
            "points_to_align": dict(self.points_to_align),
            "player_scores": dict(self.player_scores),
            "current_player": self.current_player,
            "current_turn_action": self.current_turn_action,
            "game_over": self.game_over,
            "points": points_payload,
            "traced_alignments": traced_payload,
            "alignment_keys": alignment_keys_payload,
            "alignment_reuse_counts": alignment_reuse_payload,
            "cannon_rows": dict(self.grid_window.board.cannon_rows),
        }

    def _restore_game_state(self, saved_state: dict) -> None:
        rows = int(saved_state.get("rows", 5))
        cols = int(saved_state.get("cols", 5))

        player_names = saved_state.get("player_names", {})
        points_to_align = saved_state.get("points_to_align", {})
        self.start_game(
            rows,
            cols,
            player_names.get("J1", "Joueur 1"),
            player_names.get("J2", "Joueur 2"),
            int(points_to_align.get("J1", 5)),
            int(points_to_align.get("J2", 5)),
            start_turn=False,
        )

        self.game_over = bool(saved_state.get("game_over", False))
        self.player_scores = {
            "J1": int(saved_state.get("player_scores", {}).get("J1", 0)),
            "J2": int(saved_state.get("player_scores", {}).get("J2", 0)),
        }
        current_player = saved_state.get("current_player", "J1")
        self.current_player = current_player if current_player in ("J1", "J2") else "J1"
        self.current_turn_action = None

        loaded_points = {}
        for entry in saved_state.get("points", []):
            row = int(entry.get("row", 0))
            col = int(entry.get("col", 0))
            owner = entry.get("player", "")
            if owner in ("J1", "J2"):
                loaded_points[(row, col)] = owner
        self.board_model.points = loaded_points

        self.traced_alignments = []
        for entry in saved_state.get("traced_alignments", []):
            player = entry.get("player", "")
            if player not in ("J1", "J2"):
                continue
            points = [(int(point[0]), int(point[1])) for point in entry.get("points", []) if len(point) == 2]
            if points:
                self.traced_alignments.append((points, player))

        self.alignment_keys = set()
        for entry in saved_state.get("alignment_keys", []):
            player = entry.get("player", "")
            if player not in ("J1", "J2"):
                continue
            points = tuple((int(point[0]), int(point[1])) for point in entry.get("points", []) if len(point) == 2)
            if points:
                self.alignment_keys.add((player, points))

        self.alignment_reuse_counts = {}
        for entry in saved_state.get("alignment_reuse_counts", []):
            player = entry.get("player", "")
            if player not in ("J1", "J2"):
                continue
            points = tuple((int(point[0]), int(point[1])) for point in entry.get("points", []) if len(point) == 2)
            if not points:
                continue
            reuse_count = int(entry.get("reuse_count", 0))
            self.alignment_reuse_counts[(player, points)] = max(0, reuse_count)

        for alignment_key in self.alignment_keys:
            self.alignment_reuse_counts.setdefault(alignment_key, 0)

        cannon_rows = saved_state.get("cannon_rows", {})
        self.grid_window.board.set_cannon_rows(
            {
                "J1": int(cannon_rows.get("J1", rows // 2)),
                "J2": int(cannon_rows.get("J2", rows // 2)),
            }
        )

        self.grid_window.board.set_points(self.board_model.points)
        self.grid_window.board.set_traced_alignments(self.traced_alignments)
        self.grid_window.board.set_shot_marker(None)
        self.grid_window.set_scores(
            self.player_names["J1"],
            self.player_scores["J1"],
            self.player_names["J2"],
            self.player_scores["J2"],
        )
        self.grid_window.set_current_player_key(self.current_player)
        self.grid_window.set_current_player(self.player_names[self.current_player])
        self.grid_window.set_controls_enabled(False)

        if self.game_over:
            self.current_turn_action = None
            self.turn_ready = False
            return

        self._start_turn()

    def _process_alignment_and_score(self, player: str, row: int, col: int):
        required = self._required_points_to_align(player)
        scored_points = 0

        aligned_line = self.board_model.get_aligned_points(row, col, player, required)
        if aligned_line:
            aligned_points = self._select_scoring_segment(player, aligned_line, row, col, required)
            if aligned_points:
                scored_points += self._register_alignment(player, aligned_points)

        if self._is_reduced_alignment_rule_active(player):
            scored_points += self._score_existing_alignments(player, required)

        if scored_points == 0:
            return

        self.grid_window.board.set_traced_alignments(self.traced_alignments)
        self.grid_window.set_scores(
            self.player_names["J1"],
            self.player_scores["J1"],
            self.player_names["J2"],
            self.player_scores["J2"],
        )

        if scored_points == 1:
            message = f"{self.player_names[player]} a aligné {required} points et gagne 1 point."
        else:
            message = (
                f"{self.player_names[player]} a aligné {required} points et gagne {scored_points} points."
            )

        QMessageBox.information(
            self.grid_window,
            "Point gagné",
            message,
            QMessageBox.Ok,
        )

    def _register_alignment(self, player: str, aligned_points: list[tuple[int, int]]) -> int:
        alignment_key = (player, tuple(aligned_points))
        if alignment_key in self.alignment_keys:
            return 0

        intersected_keys = self._intersected_alignment_keys(player, aligned_points)
        score_gain = self._calculate_alignment_score_gain(player, aligned_points)

        for reused_key in intersected_keys:
            reused_alignment_points_count = len(reused_key[1])
            self.alignment_reuse_counts[reused_key] = (
                self.alignment_reuse_counts.get(reused_key, 0) + reused_alignment_points_count
            )

        self.alignment_keys.add(alignment_key)
        reused_points_total = sum(len(reused_key[1]) for reused_key in intersected_keys)
        self.alignment_reuse_counts[alignment_key] = self.alignment_reuse_counts.get(alignment_key, 0) + reused_points_total
        self.traced_alignments.append((aligned_points, player))
        self.player_scores[player] += score_gain
        return score_gain

    def _intersected_alignment_keys(
        self, player: str, aligned_points: list[tuple[int, int]]
    ) -> list[tuple[str, tuple[tuple[int, int], ...]]]:
        aligned_set = set(aligned_points)
        intersected_keys: list[tuple[str, tuple[tuple[int, int], ...]]] = []

        for traced_points, traced_player in self.traced_alignments:
            if traced_player != player:
                continue
            if not aligned_set.intersection(traced_points):
                continue
            intersected_keys.append((traced_player, tuple(traced_points)))

        return intersected_keys

    def _calculate_alignment_score_gain(self, player: str, aligned_points: list[tuple[int, int]]) -> int:
        intersected_keys = self._intersected_alignment_keys(player, aligned_points)
        if not intersected_keys:
            return 1

        score_gain = 0
        for key in intersected_keys:
            reuse_after_use = self.alignment_reuse_counts.get(key, 0) + 1
            if reuse_after_use >= 2:
                score_gain += 3
            else:
                score_gain += 2

        return score_gain

    def _score_existing_alignments(self, player: str, required: int) -> int:
        if self.board_model is None:
            return 0

        scored_points = 0
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for (row, col), owner in self.board_model.points.items():
            if owner != player:
                continue

            for d_row, d_col in directions:
                previous_cell = (row - d_row, col - d_col)
                if self.board_model.points.get(previous_cell) == player:
                    continue

                line = []
                step = 0
                while self.board_model.points.get((row + d_row * step, col + d_col * step)) == player:
                    line.append((row + d_row * step, col + d_col * step))
                    step += 1

                if len(line) < required:
                    continue

                for start in range(0, len(line) - required + 1):
                    candidate = line[start : start + required]
                    candidate_key = (player, tuple(candidate))
                    if candidate_key in self.alignment_keys:
                        continue

                    direction = self._alignment_direction(candidate)
                    if self._touches_traced_alignment(player, candidate, direction):
                        continue
                    if self._intersects_other_player_alignment(player, candidate):
                        continue

                    scored_points += self._register_alignment(player, candidate)

        return scored_points

    def _is_reduced_alignment_rule_active(self, player: str) -> bool:
        base_required = self.points_to_align[player]
        if base_required <= 4:
            return False

        return self._count_player_points(player) >= 11

    def _count_player_points(self, player: str) -> int:
        if self.board_model is None:
            return 0
        return sum(1 for owner in self.board_model.points.values() if owner == player)

    def _required_points_to_align(self, player: str) -> int:
        base_required = self.points_to_align[player]
        placed_points_count = self._count_player_points(player)
        if placed_points_count >= 11:
            return min(base_required, 4)

        return base_required

    def _select_scoring_segment(
        self,
        player: str,
        aligned_line: list[tuple[int, int]],
        row: int,
        col: int,
        required: int,
    ) -> list[tuple[int, int]] | None:
        if required <= 1:
            return [(row, col)]

        try:
            center_index = aligned_line.index((row, col))
        except ValueError:
            return None

        first_start = max(0, center_index - required + 1)
        last_start = min(center_index, len(aligned_line) - required)

        for start in range(first_start, last_start + 1):
            candidate = aligned_line[start : start + required]
            alignment_key = (player, tuple(candidate))
            if alignment_key in self.alignment_keys:
                continue

            direction = self._alignment_direction(candidate)
            if self._touches_traced_alignment(player, candidate, direction):
                continue
            if self._intersects_other_player_alignment(player, candidate):
                continue

            return candidate

        return None

    def _touches_traced_alignment(
        self,
        player: str,
        aligned_points: list[tuple[int, int]],
        direction: tuple[int, int],
    ) -> bool:
        current_points = set(aligned_points)

        for traced_points, traced_player in self.traced_alignments:
            if traced_player != player or len(traced_points) < 2:
                continue

            traced_direction = self._alignment_direction(traced_points)
            if traced_direction != direction:
                continue

            traced_set = set(traced_points)
            if current_points.intersection(traced_set):
                return True

        return False

    def _intersects_other_player_alignment(self, player: str, aligned_points: list[tuple[int, int]]) -> bool:
        candidate_segments = list(zip(aligned_points, aligned_points[1:]))

        for traced_points, traced_player in self.traced_alignments:
            if traced_player == player or len(traced_points) < 2:
                continue

            traced_segments = list(zip(traced_points, traced_points[1:]))
            for seg_a_start, seg_a_end in candidate_segments:
                for seg_b_start, seg_b_end in traced_segments:
                    if self._segments_intersect(seg_a_start, seg_a_end, seg_b_start, seg_b_end):
                        return True

        return False

    def _segments_intersect(
        self,
        p1: tuple[int, int],
        p2: tuple[int, int],
        q1: tuple[int, int],
        q2: tuple[int, int],
    ) -> bool:
        o1 = self._orientation(p1, p2, q1)
        o2 = self._orientation(p1, p2, q2)
        o3 = self._orientation(q1, q2, p1)
        o4 = self._orientation(q1, q2, p2)

        if o1 != o2 and o3 != o4:
            return True

        if o1 == 0 and self._on_segment(p1, q1, p2):
            return True
        if o2 == 0 and self._on_segment(p1, q2, p2):
            return True
        if o3 == 0 and self._on_segment(q1, p1, q2):
            return True
        if o4 == 0 and self._on_segment(q1, p2, q2):
            return True

        return False

    def _orientation(self, p: tuple[int, int], q: tuple[int, int], r: tuple[int, int]) -> int:
        py, px = p
        qy, qx = q
        ry, rx = r

        value = (qy - py) * (rx - qx) - (qx - px) * (ry - qy)
        if value == 0:
            return 0
        return 1 if value > 0 else 2

    def _on_segment(self, p: tuple[int, int], q: tuple[int, int], r: tuple[int, int]) -> bool:
        py, px = p
        qy, qx = q
        ry, rx = r

        return min(py, ry) <= qy <= max(py, ry) and min(px, rx) <= qx <= max(px, rx)

    def _alignment_direction(self, aligned_points: list[tuple[int, int]]) -> tuple[int, int]:
        if len(aligned_points) < 2:
            return (0, 0)

        row1, col1 = aligned_points[0]
        row2, col2 = aligned_points[1]
        d_row = row2 - row1
        d_col = col2 - col1

        if d_row == 0:
            return (0, 1)
        if d_col == 0:
            return (1, 0)
        if d_row == d_col:
            return (1, 1)
        return (1, -1)

    def _show_turn_popup(self):
        if self.grid_window is None:
            return

        QMessageBox.information(
            self.grid_window,
            "Tour",
            f"C'est le tour de {self.player_names[self.current_player]}",
            QMessageBox.Ok,
        )
