import unittest
from pathlib import Path


PYTHON_DIR = Path(__file__).resolve().parents[1]


class IndoorTrainingContractTest(unittest.TestCase):
    def test_training_uses_balanced_class_weight(self):
        script = (PYTHON_DIR / "training" / "train.py").read_text()

        self.assertIn("def compute_class_weight(", script)
        self.assertIn("class_weight = compute_class_weight(", script)
        self.assertIn("class_weight=class_weight", script)


if __name__ == "__main__":
    unittest.main()
