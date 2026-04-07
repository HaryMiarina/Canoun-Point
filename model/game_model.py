from dataclasses import dataclass, field


@dataclass
class Dimensions:
    rows: int
    cols: int


@dataclass
class BoardModel:
    dimensions: Dimensions
    points: dict[tuple[int, int], str] = field(default_factory=dict)

    def place_point(self, row: int, col: int, player: str) -> bool:
        key = (row, col)
        if key in self.points:
            return False

        self.points[key] = player
        return True

    def remove_point(self, row: int, col: int) -> bool:
        key = (row, col)
        if key not in self.points:
            return False

        del self.points[key]
        return True

    def get_aligned_points(self, row: int, col: int, player: str, required: int) -> list[tuple[int, int]] | None:
        if required <= 1:
            return [(row, col)]

        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for d_row, d_col in directions:
            line = [(row, col)]

            step = 1
            while self.points.get((row + d_row * step, col + d_col * step)) == player:
                line.append((row + d_row * step, col + d_col * step))
                step += 1

            step = 1
            while self.points.get((row - d_row * step, col - d_col * step)) == player:
                line.insert(0, (row - d_row * step, col - d_col * step))
                step += 1

            if len(line) >= required:
                return line

        return None
