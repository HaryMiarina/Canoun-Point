from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QLabel,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
)


class DimensionWindow(QWidget):
    dimensions_submitted = pyqtSignal(int, int, str, str, int, int)
    load_game_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("DimensionWindow")
        self.setWindowTitle("Canon Point")
        self.resize(760, 240)
        self.setAttribute(Qt.WA_StyledBackground, True)
        bg_path = (Path(__file__).resolve().parent.parent / "assets" / "start_background.svg").as_posix()
        spin_up_path = (Path(__file__).resolve().parent.parent / "assets" / "spin_up_black.svg").as_posix()
        spin_down_path = (Path(__file__).resolve().parent.parent / "assets" / "spin_down_black.svg").as_posix()
        self.setStyleSheet(
            f"""
            QWidget#DimensionWindow {{
                background-image: url("{bg_path}");
                background-position: center;
                background-repeat: no-repeat;
            }}
            QWidget {{
                background-color: rgba(47, 36, 64, 0);
                color: #fff6da;
                font-size: 14px;
            }}
            QLineEdit, QSpinBox {{
                background-color: #fff3d3;
                color: #4a3112;
                border: 1px solid #f2c14e;
                border-radius: 8px;
                padding: 4px 8px;
                min-height: 28px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 20px;
                border-left: 1px solid #d39b3a;
                background-color: #ffe8b8;
            }}
            QSpinBox::up-arrow {{
                image: url("{spin_up_path}");
                width: 10px;
                height: 10px;
            }}
            QSpinBox::down-arrow {{
                image: url("{spin_down_path}");
                width: 10px;
                height: 10px;
            }}
            QLabel#MainTitle {{
                color: #fff6da;
                font-size: 44px;
                font-weight: 800;
                letter-spacing: 3px;
                padding: 6px 14px;
                background-color: rgba(43, 28, 22, 140);
                border: 2px solid #ffd88b;
                border-radius: 14px;
            }}
            QPushButton {{
                background-color: #f2c14e;
                color: #3d2c13;
                border: 1px solid #ffebad;
                border-radius: 10px;
                padding: 8px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #ffd770;
            }}
            QPushButton:pressed {{
                background-color: #ddad3a;
            }}
            """
        )

        self.length_input = QSpinBox()
        self.length_input.setRange(1, 500)
        self.length_input.setValue(5)

        self.width_input = QSpinBox()
        self.width_input.setRange(1, 500)
        self.width_input.setValue(5)

        self.player1_name_input = QLineEdit()
        self.player1_name_input.setText("Joueur 1")

        self.player2_name_input = QLineEdit()
        self.player2_name_input.setText("Joueur 2")

        self.points_to_align_j1_input = QSpinBox()
        self.points_to_align_j1_input.setRange(2, 500)
        self.points_to_align_j1_input.setValue(5)

        self.points_to_align_j2_input = QSpinBox()
        self.points_to_align_j2_input.setRange(2, 500)
        self.points_to_align_j2_input.setValue(5)

        open_button = QPushButton("Créer la grille")
        open_button.clicked.connect(self._emit_dimensions)
        load_button = QPushButton("Charger partie")
        load_button.clicked.connect(self.load_game_requested.emit)

        title_label = QLabel("CANON POINT")
        title_label.setObjectName("MainTitle")
        title_label.setAlignment(Qt.AlignCenter)

        form_layout = QFormLayout()
        form_layout.addRow("Longueur :", self.length_input)
        form_layout.addRow("Largeur :", self.width_input)

        players_form_layout = QFormLayout()
        players_form_layout.addRow("Nom J1 :", self.player1_name_input)
        players_form_layout.addRow("Nom J2 :", self.player2_name_input)
        players_form_layout.addRow("Points à aligner J1 :", self.points_to_align_j1_input)
        players_form_layout.addRow("Points à aligner J2 :", self.points_to_align_j2_input)

        form_container = QWidget()
        form_container.setMaximumWidth(260)
        form_container_layout = QVBoxLayout(form_container)
        form_container_layout.setContentsMargins(0, 0, 0, 0)
        form_container_layout.addLayout(form_layout)
        form_container_layout.addWidget(open_button)
        form_container_layout.addWidget(load_button)

        players_container = QWidget()
        players_container.setMaximumWidth(300)
        players_container_layout = QVBoxLayout(players_container)
        players_container_layout.setContentsMargins(0, 0, 0, 0)
        players_container_layout.addLayout(players_form_layout)

        center_row = QHBoxLayout()
        center_row.addStretch()
        center_row.addWidget(form_container)
        center_row.addSpacing(24)
        center_row.addWidget(players_container)
        center_row.addStretch()

        main_layout = QVBoxLayout(self)
        main_layout.addSpacing(8)
        main_layout.addWidget(title_label, alignment=Qt.AlignHCenter)
        main_layout.addStretch()
        main_layout.addLayout(center_row)
        main_layout.addStretch()

    def _emit_dimensions(self):
        player1_name = self.player1_name_input.text().strip() or "Joueur 1"
        player2_name = self.player2_name_input.text().strip() or "Joueur 2"
        self.dimensions_submitted.emit(
            self.length_input.value(),
            self.width_input.value(),
            player1_name,
            player2_name,
            self.points_to_align_j1_input.value(),
            self.points_to_align_j2_input.value(),
        )
