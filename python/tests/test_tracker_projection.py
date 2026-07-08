import unittest

import numpy as np

from tracker.config import (
    GRID_CELL_SIZE_CM,
    GRID_COLUMNS,
    GRID_ROWS,
    TRACKING_AREA_HEIGHT_CM,
    TRACKING_AREA_WIDTH_CM,
)
from tracker.runtime import (
    create_center_cell_destination_points,
    create_inverse_perspective_matrix,
    project_destination_point_to_source,
)


class TrackerProjectionTest(unittest.TestCase):
    def test_center_cell_destination_points_use_middle_grid_square(self):
        points = create_center_cell_destination_points()
        center_column = GRID_COLUMNS // 2
        center_row = GRID_ROWS // 2
        left = center_column * GRID_CELL_SIZE_CM
        top = center_row * GRID_CELL_SIZE_CM

        np.testing.assert_array_equal(
            points,
            np.array(
                [
                    [left, top],
                    [left + GRID_CELL_SIZE_CM, top],
                    [left + GRID_CELL_SIZE_CM, top + GRID_CELL_SIZE_CM],
                    [left, top + GRID_CELL_SIZE_CM],
                ],
                dtype=float,
            ),
        )

    def test_projects_outer_corners_from_center_cell_homography(self):
        center_cell_source = np.array(
            [
                [100.0, 100.0],
                [200.0, 100.0],
                [200.0, 200.0],
                [100.0, 200.0],
            ],
            dtype=float,
        )

        inverse_matrix = create_inverse_perspective_matrix(center_cell_source)

        top_left = project_destination_point_to_source(inverse_matrix, 0.0, 0.0)
        bottom_right = project_destination_point_to_source(
            inverse_matrix, TRACKING_AREA_WIDTH_CM, TRACKING_AREA_HEIGHT_CM
        )

        np.testing.assert_allclose(top_left, np.array([0.0, 0.0]), atol=1e-4)
        np.testing.assert_allclose(bottom_right, np.array([300.0, 300.0]), atol=1e-4)


if __name__ == "__main__":
    unittest.main()
