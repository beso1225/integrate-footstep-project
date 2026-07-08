import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class GridDefinition:
    columns: int
    rows: int
    cell_size_cm: float

    @property
    def width_cm(self):
        return self.columns * self.cell_size_cm

    @property
    def height_cm(self):
        return self.rows * self.cell_size_cm

    def adjust_columns(self, step):
        return GridDefinition(
            columns=max(1, self.columns + step * 2),
            rows=self.rows,
            cell_size_cm=self.cell_size_cm,
        )

    def adjust_rows(self, step):
        return GridDefinition(
            columns=self.columns,
            rows=max(1, self.rows + step * 2),
            cell_size_cm=self.cell_size_cm,
        )

    def adjust_cell_size(self, delta_cm):
        adjusted = round(max(1.0, self.cell_size_cm + delta_cm), 1)
        return GridDefinition(
            columns=self.columns,
            rows=self.rows,
            cell_size_cm=adjusted,
        )

    def to_dict(self):
        return {
            "columns": self.columns,
            "rows": self.rows,
            "cell_size_cm": self.cell_size_cm,
        }


def load_grid_definition(path):
    payload = json.loads(Path(path).read_text())
    return GridDefinition(
        columns=int(payload["columns"]),
        rows=int(payload["rows"]),
        cell_size_cm=float(payload["cell_size_cm"]),
    )


def load_calibration_points(path):
    payload = json.loads(Path(path).read_text())
    calibration_points = payload.get("calibration_points")
    if calibration_points is None:
        return None
    return np.array(calibration_points, dtype=float)


def save_grid_definition(grid_definition, path, calibration_points=None):
    payload = grid_definition.to_dict()
    if calibration_points is not None:
        payload["calibration_points"] = np.asarray(calibration_points, dtype=float).tolist()
    Path(path).write_text(json.dumps(payload, indent=2) + "\n")
