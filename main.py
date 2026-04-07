import sys

from PyQt5.QtWidgets import QApplication

from controller.game_controller import GameController


def main():
    app = QApplication(sys.argv)
    controller = GameController()
    controller.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
