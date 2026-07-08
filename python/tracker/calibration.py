from dataclasses import dataclass, field

import numpy as np


@dataclass
class CalibrationState:
    points: np.ndarray
    handle_radius: float = 20.0
    dragging_index: int | None = field(default=None, init=False)

    def start_drag(self, x, y):
        index = self.find_nearest_point(x, y)
        if index is None:
            return False
        self.dragging_index = index
        return True

    def drag_to(self, x, y):
        if self.dragging_index is None:
            return False
        self.points[self.dragging_index] = [float(x), float(y)]
        return True

    def stop_drag(self):
        self.dragging_index = None

    def find_nearest_point(self, x, y):
        target = np.array([float(x), float(y)])
        for index, point in enumerate(self.points):
            if np.linalg.norm(point - target) <= self.handle_radius:
                return index
        return None
