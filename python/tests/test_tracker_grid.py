import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from tracker.grid import (
    GridDefinition,
    load_calibration_points,
    load_grid_definition,
    save_grid_definition,
)


class GridDefinitionTest(unittest.TestCase):
    def test_adjust_columns_keeps_positive_odd_values(self):
        grid = GridDefinition(columns=3, rows=3, cell_size_cm=50.3)

        self.assertEqual(grid.adjust_columns(-1).columns, 1)
        self.assertEqual(grid.adjust_columns(1).columns, 5)

    def test_adjust_rows_keeps_positive_odd_values(self):
        grid = GridDefinition(columns=3, rows=3, cell_size_cm=50.3)

        self.assertEqual(grid.adjust_rows(-1).rows, 1)
        self.assertEqual(grid.adjust_rows(1).rows, 5)

    def test_adjust_cell_size_clamps_to_minimum(self):
        grid = GridDefinition(columns=3, rows=3, cell_size_cm=1.2)

        self.assertEqual(grid.adjust_cell_size(-1.0).cell_size_cm, 1.0)
        self.assertEqual(grid.adjust_cell_size(0.5).cell_size_cm, 1.7)

    def test_save_and_load_round_trip_grid_config(self):
        grid = GridDefinition(columns=5, rows=7, cell_size_cm=30.0)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "indoor_grid.json"
            save_grid_definition(grid, path)
            loaded = load_grid_definition(path)

        self.assertEqual(loaded, grid)

    def test_serialized_grid_config_uses_expected_keys(self):
        grid = GridDefinition(columns=5, rows=7, cell_size_cm=30.0)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "indoor_grid.json"
            save_grid_definition(grid, path)
            payload = json.loads(path.read_text())

        self.assertEqual(payload, {"columns": 5, "rows": 7, "cell_size_cm": 30.0})

    def test_save_and_load_round_trip_calibration_points(self):
        grid = GridDefinition(columns=5, rows=7, cell_size_cm=30.0)
        calibration_points = np.array(
            [[10.0, 20.0], [30.0, 40.0], [50.0, 60.0], [70.0, 80.0]],
            dtype=float,
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "indoor_grid.json"
            save_grid_definition(grid, path, calibration_points)
            loaded = load_calibration_points(path)

        np.testing.assert_array_equal(loaded, calibration_points)

    def test_missing_calibration_points_returns_none(self):
        grid = GridDefinition(columns=5, rows=7, cell_size_cm=30.0)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "indoor_grid.json"
            save_grid_definition(grid, path)

            loaded = load_calibration_points(path)

        self.assertIsNone(loaded)


if __name__ == "__main__":
    unittest.main()
