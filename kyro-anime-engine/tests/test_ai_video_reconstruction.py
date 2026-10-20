"""Tests for safe conversion of reference frames into native KAE vector cels."""
import unittest

from backend.app.exceptions import ApiError
from backend.api.ai_studio import _validated_vector_frames


class VideoReconstructionValidationTests(unittest.TestCase):
    def test_normalized_path_coordinates_convert_to_canvas_pixels(self):
        plan = [{
            "timestamp_seconds": 0,
            "strokes": [{
                "color": "#222222",
                "width": 3,
                "closed": False,
                "fill": None,
                "commands": [["M", 100, 100], ["L", 200, 200]],
            }],
        }]
        result = _validated_vector_frames(plan, 1920, 1080)
        self.assertEqual(result[0]["strokes"][0]["commands"], [["M", 192.0, 108.0], ["L", 384.0, 216.0]])
        self.assertGreater(result[0]["strokes"][0]["width"], 0)

    def test_pixel_paths_can_be_revalidated_without_double_scaling(self):
        pixel_plan = [{
            "strokes": [{
                "color": "#222222",
                "width": 5.76,
                "closed": False,
                "fill": None,
                "commands": [["M", 192, 108], ["L", 384, 216]],
            }],
        }]
        result = _validated_vector_frames(pixel_plan, 1920, 1080, coordinates_normalized=False)
        self.assertEqual(result[0]["strokes"][0]["commands"], [["M", 192.0, 108.0], ["L", 384.0, 216.0]])
        self.assertEqual(result[0]["strokes"][0]["width"], 5.76)

    def test_invalid_color_is_rejected(self):
        plan = [{
            "strokes": [{
                "color": "not-a-color",
                "width": 3,
                "closed": False,
                "fill": None,
                "commands": [["M", 100, 100], ["L", 200, 200]],
            }],
        }]
        with self.assertRaises(ApiError):
            _validated_vector_frames(plan, 1920, 1080)


if __name__ == "__main__":
    unittest.main()
