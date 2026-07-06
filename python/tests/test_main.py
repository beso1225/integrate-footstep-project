import unittest
from unittest.mock import patch

import main


class FakeModel:
    def predict_proba(self, features):
        self.columns = list(features.columns)
        return [[0.25, 0.75]]

    def predict(self, features):
        self.columns = list(features.columns)
        return [1]


class FakeClient:
    def __init__(self):
        self.messages = []

    def send_message(self, address, value):
        self.messages.append((address, value))


class StepHandlerTest(unittest.TestCase):
    def test_forwards_outdoor_step_to_processing(self):
        model = FakeModel()
        client = FakeClient()
        values = [float(index) for index in range(15)]

        with (
            patch.object(main, "model", model),
            patch.object(main, "processing_client", client),
        ):
            main.step_handler("/step/features", *values)

        self.assertEqual(model.columns, main.MODEL_FEATURE_KEYS)
        self.assertIn(("/walking/prediction", 2), client.messages)
        self.assertIn(("/walking/heading_change", 13.0), client.messages)
        self.assertIn(("/walking/step_length", 14.0), client.messages)
        self.assertEqual(client.messages[-1], ("/walking/peak_g", 0.0))
        self.assertNotIn("/step", [address for address, _ in client.messages])

    def test_rejects_incomplete_feature_payload(self):
        client = FakeClient()

        with patch.object(main, "processing_client", client):
            main.step_handler("/step/features", *([0.0] * 14))

        self.assertEqual(client.messages, [])


if __name__ == "__main__":
    unittest.main()
