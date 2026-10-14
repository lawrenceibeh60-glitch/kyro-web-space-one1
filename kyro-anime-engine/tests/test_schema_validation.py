"""Milestone A: JSON Schema Draft 2020-12 validation tests.

Validates drawing documents against formats/schemas/drawing.schema.json
using the jsonschema library.
"""
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "formats" / "schemas"


def _load_schema(name):
    with open(SCHEMAS_DIR / name) as f:
        return json.load(f)


DRAWING_SCHEMA = _load_schema("drawing.schema.json")
PATH_SCHEMA = _load_schema("path.schema.json")

# Build a registry so cross-schema $refs resolve correctly
_registry = Registry().with_resources(
    [
        ("drawing.schema.json", Resource.from_contents(DRAWING_SCHEMA)),
        ("path.schema.json", Resource.from_contents(PATH_SCHEMA)),
    ]
)
VALIDATOR = Draft202012Validator(DRAWING_SCHEMA, registry=_registry)


def _valid_drawing():
    return {
        "id": "draw_01",
        "strokes": [
            {
                "id": "s1",
                "points": [[0, 0], [10, 10]],
                "color": "#000000",
                "width": 2,
            }
        ],
    }


class TestDrawingSchemaValidation(unittest.TestCase):
    def test_valid_point_stroke(self):
        drawing = _valid_drawing()
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertEqual(errors, [])

    def test_valid_command_stroke(self):
        drawing = {
            "id": "draw_02",
            "strokes": [
                {
                    "id": "s1",
                    "commands": [["M", 0, 0], ["L", 10, 10]],
                    "color": "#ff0000",
                    "width": 1,
                }
            ],
        }
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertEqual(errors, [])

    def test_missing_id_rejected(self):
        drawing = _valid_drawing()
        del drawing["id"]
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_missing_strokes_rejected(self):
        drawing = _valid_drawing()
        del drawing["strokes"]
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_both_points_and_commands_rejected(self):
        drawing = {
            "id": "draw_bad",
            "strokes": [
                {
                    "id": "s1",
                    "points": [[0, 0]],
                    "commands": [["M", 0, 0]],
                }
            ],
        }
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_neither_points_nor_commands_rejected(self):
        drawing = {
            "id": "draw_bad2",
            "strokes": [{"id": "s1"}],
        }
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_invalid_color_format_rejected(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["color"] = "red"
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_invalid_fill_rule_rejected(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["fill_rule"] = "invalid"
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_invalid_line_cap_rejected(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["line_cap"] = "triangle"
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_invalid_line_join_rejected(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["line_join"] = "diamond"
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_zero_width_rejected(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["width"] = 0
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_negative_width_rejected(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["width"] = -1
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_opacity_out_of_range_rejected(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["opacity"] = 1.5
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_smoothing_out_of_range_rejected(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["smoothing"] = -0.1
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_invalid_tool_rejected(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["tool"] = "pencil"
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_empty_points_array_rejected(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["points"] = []
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_point_with_one_coord_rejected(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["points"] = [[0]]
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_point_with_pressure_accepted(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["points"] = [[0, 0, 0.5]]
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertEqual(errors, [])

    def test_fill_null_accepted(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["fill"] = None
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertEqual(errors, [])

    def test_fill_color_accepted(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["fill"] = "#00ff00"
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertEqual(errors, [])

    def test_additional_properties_rejected(self):
        drawing = _valid_drawing()
        drawing["unknown_field"] = True
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_stroke_additional_properties_rejected(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["unknown_prop"] = 42
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_invalid_id_pattern_rejected(self):
        drawing = _valid_drawing()
        drawing["id"] = "has spaces!"
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_closed_boolean_accepted(self):
        drawing = _valid_drawing()
        drawing["strokes"][0]["closed"] = True
        errors = list(VALIDATOR.iter_errors(drawing))
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()