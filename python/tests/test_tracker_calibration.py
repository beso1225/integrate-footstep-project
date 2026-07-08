import unittest

import numpy as np

from tracker.calibration import CalibrationState


class CalibrationStateTest(unittest.TestCase):
    def test_starts_dragging_when_click_is_near_a_corner(self):
        state = CalibrationState(
            points=np.array([[10.0, 10.0], [30.0, 10.0], [30.0, 30.0], [10.0, 30.0]])
        )

        started = state.start_drag(12, 13)

        self.assertTrue(started)
        self.assertEqual(state.dragging_index, 0)

    def test_does_not_start_dragging_when_click_is_far_from_all_corners(self):
        state = CalibrationState(
            points=np.array([[10.0, 10.0], [30.0, 10.0], [30.0, 30.0], [10.0, 30.0]])
        )

        started = state.start_drag(100, 100)

        self.assertFalse(started)
        self.assertIsNone(state.dragging_index)

    def test_updates_only_selected_corner_while_dragging(self):
        state = CalibrationState(
            points=np.array([[10.0, 10.0], [30.0, 10.0], [30.0, 30.0], [10.0, 30.0]])
        )
        state.start_drag(10, 10)

        moved = state.drag_to(50, 60)

        self.assertTrue(moved)
        np.testing.assert_array_equal(state.points[0], np.array([50.0, 60.0]))
        np.testing.assert_array_equal(state.points[1], np.array([30.0, 10.0]))

    def test_ignores_drag_requests_when_no_corner_is_selected(self):
        state = CalibrationState(
            points=np.array([[10.0, 10.0], [30.0, 10.0], [30.0, 30.0], [10.0, 30.0]])
        )

        moved = state.drag_to(50, 60)

        self.assertFalse(moved)
        np.testing.assert_array_equal(
            state.points,
            np.array([[10.0, 10.0], [30.0, 10.0], [30.0, 30.0], [10.0, 30.0]]),
        )

    def test_stops_dragging_on_release(self):
        state = CalibrationState(
            points=np.array([[10.0, 10.0], [30.0, 10.0], [30.0, 30.0], [10.0, 30.0]])
        )
        state.start_drag(10, 10)

        state.stop_drag()

        self.assertIsNone(state.dragging_index)


if __name__ == "__main__":
    unittest.main()
