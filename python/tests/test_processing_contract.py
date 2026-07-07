from pathlib import Path
import re
import unittest


SKETCH_DIR = Path(__file__).resolve().parents[2] / "processing"


class ProcessingContractTest(unittest.TestCase):
    def setUp(self):
        self.sketch = "\n".join(
            path.read_text() for path in sorted(SKETCH_DIR.glob("*.pde"))
        )

    def test_sketch_is_split_by_responsibility(self):
        expected_files = {
            "processing.pde",
            "Config.pde",
            "Drawing.pde",
            "Emotion.pde",
            "Indoor.pde",
            "OscHandlers.pde",
            "Outdoor.pde",
        }
        actual_files = {path.name for path in SKETCH_DIR.glob("*.pde")}
        self.assertTrue(expected_files.issubset(actual_files))

    def constant(self, name):
        match = re.search(rf"final float {name} = ([0-9.]+);", self.sketch)
        self.assertIsNotNone(match, f"Missing Processing constant: {name}")
        return float(match.group(1))

    def test_sketch_uses_available_assets(self):
        for movie in ("happy", "sad", "neutral"):
            relative_path = f"movie/{movie}.mp4"
            self.assertIn(f'new Movie(this, "{relative_path}")', self.sketch)
            self.assertTrue((SKETCH_DIR / "data" / relative_path).is_file())

        self.assertIn('loadImage("img/footprint.png")', self.sketch)
        self.assertTrue((SKETCH_DIR / "data/img/footprint.png").is_file())

    def test_sketch_accepts_both_input_routes(self):
        self.assertIn('msg.checkAddrPattern("/footstep")', self.sketch)
        self.assertIn('msg.checkAddrPattern("/walking/prediction")', self.sketch)
        self.assertIn('msg.checkAddrPattern("/walking/peak_g")', self.sketch)
        self.assertIn("indoorEmotionFromMessage(msg)", self.sketch)

    def test_physical_dimensions_are_explicit(self):
        self.assertGreater(self.constant("PIXELS_PER_METER"), 0.0)
        self.assertGreater(self.constant("FOOT_LENGTH_CM"), 0.0)
        ratio = self.constant("FOOT_WIDTH_TO_LENGTH_RATIO")
        self.assertGreater(ratio, 0.0)
        self.assertLessEqual(ratio, 1.0)
        self.assertIn("footHeight = round(cmToPixels(FOOT_LENGTH_CM));", self.sketch)

    def test_indoor_and_outdoor_gait_ranges_are_explicit(self):
        self.assertGreater(self.constant("INDOOR_STEP_TRIGGER_CM"), 0.0)
        minimum = self.constant("OUTDOOR_MIN_STEP_LENGTH_CM")
        default = self.constant("OUTDOOR_DEFAULT_STEP_LENGTH_CM")
        maximum = self.constant("OUTDOOR_MAX_STEP_LENGTH_CM")
        self.assertLessEqual(minimum, default)
        self.assertLessEqual(default, maximum)
        self.assertGreater(self.constant("INDOOR_STEP_WIDTH_CM"), 0.0)
        self.assertGreater(self.constant("OUTDOOR_STEP_WIDTH_CM"), 0.0)
        self.assertIn("inputStepLengthMeters * 100.0", self.sketch)
        self.assertIn(
            "fp.isRight ? fp.lateralOffset : -fp.lateralOffset", self.sketch
        )

    def test_indoor_heading_uses_transformed_screen_coordinates(self):
        self.assertIn(
            "PVector previousScreen = indoorToScreen(w.prevRealX, w.prevRealY);",
            self.sketch,
        )
        self.assertIn(
            "PVector currentScreen = indoorToScreen(realX, realY);", self.sketch
        )
        self.assertIn(
            "atan2(currentScreen.y - previousScreen.y, currentScreen.x - previousScreen.x)",
            self.sketch,
        )
        self.assertNotIn(
            "atan2(realY - w.prevRealY, realX - w.prevRealX)", self.sketch
        )

    def test_outdoor_turn_is_limited_to_prevent_foot_crossing(self):
        maximum = self.constant("OUTDOOR_MAX_TURN_DEGREES")
        self.assertGreater(maximum, 0.0)
        self.assertLess(maximum, 90.0)
        self.assertIn("float angleDelta = inputHeadingChangeRadians;", self.sketch)
        self.assertIn(
            "constrain(angleDelta, -maxTurnRadians, maxTurnRadians)", self.sketch
        )
        self.assertIn(
            "currentAngle = (currentAngle + angleDelta + TWO_PI) % TWO_PI;",
            self.sketch,
        )
        self.assertNotIn("radians(inputHeadingChangeDegrees)", self.sketch)
        self.assertNotIn("if (abs(angleDelta) > 10.0)", self.sketch)

    def test_random_turn_follows_the_side_of_the_next_foot(self):
        click_maximum = self.constant("CLICK_MAX_TURN_DEGREES")
        runtime_maximum = self.constant("OUTDOOR_MAX_TURN_DEGREES")
        self.assertGreater(click_maximum, 0.0)
        self.assertLessEqual(click_maximum, 8.0)
        self.assertLessEqual(click_maximum, runtime_maximum)
        self.assertIn(
            "float magnitude = random(0, CLICK_MAX_TURN_DEGREES);",
            self.sketch,
        )
        self.assertIn("radians(randomTurnForFoot(isRightFoot))", self.sketch)

    def test_indoor_emotion_payload_is_optional_and_normalized(self):
        self.assertIn("String indoorEmotionFromMessage(OscMessage msg)", self.sketch)
        self.assertIn('msg.arguments().length >= 4', self.sketch)
        self.assertIn('return normalizeEmotion(msg.get(3).stringValue());', self.sketch)
        self.assertIn('return "happy";', self.sketch)
        self.assertIn("normalizeEmotion(String emotion)", self.sketch)
        self.assertIn("emotion.toLowerCase()", self.sketch)
        self.assertIn('if (normalizedEmotion.equals("angry")) return "sad";', self.sketch)
        self.assertIn("return rightFoot ? magnitude : -magnitude;", self.sketch)
        self.assertIn("randomTurnForFoot(isRightFoot)", self.sketch)
        self.assertNotIn(
            "random(-CLICK_MAX_TURN_DEGREES, CLICK_MAX_TURN_DEGREES)",
            self.sketch,
        )


if __name__ == "__main__":
    unittest.main()
