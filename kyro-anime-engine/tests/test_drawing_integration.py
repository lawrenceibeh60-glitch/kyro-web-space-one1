"""Milestone A: integration tests for drawing foundation stability.

Verifies that point strokes and path (commands) strokes both pass
validation and round-trip through the drawing service, and that
malformed stroke data is rejected.
"""
import unittest

from backend.services.drawing_service import create_drawing, update_drawing
from backend.services.validation_service import validate_project
from backend.storage import project_repository as repo


def _minimal_project(project_id):
    """Return a minimal valid project document."""
    return {
        "format": "kae",
        "version": 1,
        "id": project_id,
        "name": "Test Project",
        "settings": {
            "width": 1280,
            "height": 720,
            "fps": 12,
            "duration_frames": 24,
            "background": "#ffffff",
        },
        "drawings": {},
        "scenes": [
            {
                "id": "scene_01",
                "layers": [
                    {"id": "layer_01", "type": "drawing"}
                ],
            }
        ],
    }


class TestDrawingIntegration(unittest.TestCase):
    def setUp(self):
        self.project_id = "test_drawing_integ"
        self.project = _minimal_project(self.project_id)
        repo.save(self.project_id, self.project)

    def tearDown(self):
        try:
            repo.delete(self.project_id)
        except Exception:
            pass

    def test_point_stroke_round_trip(self):
        point_drawing = {
            "id": "draw_points",
            "name": "Points",
            "strokes": [
                {
                    "id": "s1",
                    "tool": "brush",
                    "color": "#000000",
                    "width": 2,
                    "points": [[0, 0], [10, 10], [20, 0]],
                }
            ],
        }
        created = create_drawing(self.project_id, point_drawing)
        self.assertEqual(created["id"], "draw_points")
        self.assertEqual(len(created["strokes"]), 1)
        self.assertIn("points", created["strokes"][0])

    def test_path_commands_stroke_round_trip(self):
        path_drawing = {
            "id": "draw_paths",
            "name": "Paths",
            "strokes": [
                {
                    "id": "s2",
                    "tool": "pen",
                    "color": "#ff0000",
                    "width": 3,
                    "commands": [["M", 0, 0], ["L", 10, 10], ["Q", 15, 5, 20, 0]],
                }
            ],
        }
        created = create_drawing(self.project_id, path_drawing)
        self.assertEqual(created["id"], "draw_paths")
        self.assertIn("commands", created["strokes"][0])

    def test_update_point_to_path_stroke(self):
        point_drawing = {
            "id": "draw_convert",
            "name": "Convert",
            "strokes": [
                {
                    "id": "s3",
                    "tool": "brush",
                    "color": "#000000",
                    "width": 2,
                    "points": [[0, 0], [10, 10]],
                }
            ],
        }
        create_drawing(self.project_id, point_drawing)

        updated = update_drawing(
            self.project_id,
            "draw_convert",
            {
                "strokes": [
                    {
                        "id": "s3_new",
                        "tool": "pen",
                        "color": "#000000",
                        "width": 2,
                        "commands": [["M", 0, 0], ["L", 10, 10]],
                    }
                ]
            },
        )
        self.assertIn("commands", updated["strokes"][0])
        self.assertNotIn("points", updated["strokes"][0])

    def test_fill_rule_and_line_styles_accepted(self):
        styled_drawing = {
            "id": "draw_styled",
            "name": "Styled",
            "strokes": [
                {
                    "id": "s4",
                    "tool": "brush",
                    "color": "#00ff00",
                    "width": 1,
                    "points": [[0, 0], [10, 0], [10, 10], [0, 10]],
                    "closed": True,
                    "fill": "#00ff00",
                    "fill_rule": "evenodd",
                    "line_cap": "square",
                    "line_join": "bevel",
                }
            ],
        }
        created = create_drawing(self.project_id, styled_drawing)
        stroke = created["strokes"][0]
        self.assertEqual(stroke["fill_rule"], "evenodd")
        self.assertEqual(stroke["line_cap"], "square")
        self.assertEqual(stroke["line_join"], "bevel")

    def test_malformed_stroke_rejected_by_validation(self):
        bad_project = _minimal_project("bad_proj")
        bad_project["drawings"] = {
            "d1": {
                "id": "d1",
                "strokes": [
                    {"id": "s_bad", "points": [[0, 0], [10, "invalid"]]}
                ],
            }
        }
        errs = validate_project(bad_project)
        self.assertTrue(any("points" in e for e in errs))

    def test_stroke_with_both_points_and_commands_rejected(self):
        bad_project = _minimal_project("bad_proj2")
        bad_project["drawings"] = {
            "d2": {
                "id": "d2",
                "strokes": [
                    {
                        "id": "s_both",
                        "points": [[0, 0]],
                        "commands": [["M", 0, 0]],
                    }
                ],
            }
        }
        errs = validate_project(bad_project)
        self.assertTrue(any("exactly one" in e for e in errs))


if __name__ == "__main__":
    unittest.main()