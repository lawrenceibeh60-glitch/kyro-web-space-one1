"""Milestone B: Style, dash, gradient, and compound fill (holes) tests.

Validates style.schema.json standalone, drawing.schema.json with new
style/dash/holes properties, and programmatic validation_service checks.
"""
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "formats" / "schemas"


def _load(name):
    with open(SCHEMAS_DIR / name) as f:
        return json.load(f)


DRAWING_SCHEMA = _load("drawing.schema.json")
PATH_SCHEMA = _load("path.schema.json")
STYLE_SCHEMA = _load("style.schema.json")

_REGISTRY = Registry().with_resources(
    [
        ("drawing.schema.json", Resource.from_contents(DRAWING_SCHEMA)),
        ("path.schema.json", Resource.from_contents(PATH_SCHEMA)),
        ("style.schema.json", Resource.from_contents(STYLE_SCHEMA)),
    ]
)

STYLE_VALIDATOR = Draft202012Validator(STYLE_SCHEMA, registry=_REGISTRY)
DRAWING_VALIDATOR = Draft202012Validator(DRAWING_SCHEMA, registry=_REGISTRY)

from backend.services.validation_service import validate_project


def _minimal_project():
    return {
        "format": "kae",
        "version": 1,
        "id": "proj_01",
        "name": "Test",
        "settings": {"fps": 24, "duration_frames": 10, "width": 800, "height": 600},
        "scenes": [{"id": "scene_01", "layers": [{"id": "layer_01", "type": "drawing"}]}],
        "drawings": {},
    }


# ---------------------------------------------------------------------------
# Style schema tests
# ---------------------------------------------------------------------------

class TestStyleSchema(unittest.TestCase):
    def test_valid_dash_style(self):
        style = {"id": "dash_01", "name": "Dashed", "dash": {"array": [5, 3]}}
        errors = list(STYLE_VALIDATOR.iter_errors(style))
        self.assertEqual(errors, [])

    def test_valid_dash_with_offset(self):
        style = {"id": "s1", "dash": {"array": [10, 5, 2], "offset": 3}}
        errors = list(STYLE_VALIDATOR.iter_errors(style))
        self.assertEqual(errors, [])

    def test_dash_empty_array_rejected(self):
        style = {"id": "s1", "dash": {"array": []}}
        errors = list(STYLE_VALIDATOR.iter_errors(style))
        self.assertTrue(len(errors) > 0)

    def test_dash_zero_value_rejected(self):
        style = {"id": "s1", "dash": {"array": [5, 0, 3]}}
        errors = list(STYLE_VALIDATOR.iter_errors(style))
        self.assertTrue(len(errors) > 0)

    def test_dash_negative_value_rejected(self):
        style = {"id": "s1", "dash": {"array": [-1, 5]}}
        errors = list(STYLE_VALIDATOR.iter_errors(style))
        self.assertTrue(len(errors) > 0)

    def test_dash_too_many_items_rejected(self):
        style = {"id": "s1", "dash": {"array": list(range(1, 18))}}
        errors = list(STYLE_VALIDATOR.iter_errors(style))
        self.assertTrue(len(errors) > 0)

    def test_valid_linear_gradient(self):
        style = {
            "id": "g1",
            "gradient": {
                "type": "linear",
                "x0": 0, "y0": 0, "x1": 1, "y1": 1,
                "stops": [
                    {"offset": 0, "color": "#ff0000"},
                    {"offset": 1, "color": "#0000ff"},
                ],
            },
        }
        errors = list(STYLE_VALIDATOR.iter_errors(style))
        self.assertEqual(errors, [])

    def test_valid_radial_gradient(self):
        style = {
            "id": "g2",
            "gradient": {
                "type": "radial",
                "r0": 0, "r1": 50,
                "stops": [
                    {"offset": 0, "color": "#ffffff"},
                    {"offset": 0.5, "color": "#888888"},
                    {"offset": 1, "color": "#000000ff"},
                ],
            },
        }
        errors = list(STYLE_VALIDATOR.iter_errors(style))
        self.assertEqual(errors, [])

    def test_gradient_missing_stops_rejected(self):
        style = {"id": "g3", "gradient": {"type": "linear"}}
        errors = list(STYLE_VALIDATOR.iter_errors(style))
        self.assertTrue(len(errors) > 0)

    def test_gradient_single_stop_rejected(self):
        style = {
            "id": "g4",
            "gradient": {
                "type": "linear",
                "stops": [{"offset": 0, "color": "#ff0000"}],
            },
        }
        errors = list(STYLE_VALIDATOR.iter_errors(style))
        self.assertTrue(len(errors) > 0)

    def test_gradient_offset_out_of_range_rejected(self):
        style = {
            "id": "g5",
            "gradient": {
                "type": "linear",
                "stops": [
                    {"offset": 0, "color": "#ff0000"},
                    {"offset": 1.5, "color": "#0000ff"},
                ],
            },
        }
        errors = list(STYLE_VALIDATOR.iter_errors(style))
        self.assertTrue(len(errors) > 0)

    def test_gradient_invalid_color_rejected(self):
        style = {
            "id": "g6",
            "gradient": {
                "type": "linear",
                "stops": [
                    {"offset": 0, "color": "red"},
                    {"offset": 1, "color": "#0000ff"},
                ],
            },
        }
        errors = list(STYLE_VALIDATOR.iter_errors(style))
        self.assertTrue(len(errors) > 0)

    def test_gradient_invalid_type_rejected(self):
        style = {
            "id": "g7",
            "gradient": {
                "type": "conic",
                "stops": [
                    {"offset": 0, "color": "#ff0000"},
                    {"offset": 1, "color": "#0000ff"},
                ],
            },
        }
        errors = list(STYLE_VALIDATOR.iter_errors(style))
        self.assertTrue(len(errors) > 0)


# ---------------------------------------------------------------------------
# Drawing schema – dash / style_id on strokes
# ---------------------------------------------------------------------------

class TestDrawingSchemaDashAndStyle(unittest.TestCase):
    def _base_stroke(self, **extra):
        s = {"id": "s1", "points": [[0, 0], [10, 10]]}
        s.update(extra)
        return {"id": "d1", "strokes": [s]}

    def test_stroke_with_dash(self):
        drawing = self._base_stroke(dash=[5, 3])
        errors = list(DRAWING_VALIDATOR.iter_errors(drawing))
        self.assertEqual(errors, [])

    def test_stroke_with_dash_and_offset(self):
        drawing = self._base_stroke(dash=[10, 5], dash_offset=2)
        errors = list(DRAWING_VALIDATOR.iter_errors(drawing))
        self.assertEqual(errors, [])

    def test_stroke_dash_zero_rejected(self):
        drawing = self._base_stroke(dash=[5, 0])
        errors = list(DRAWING_VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_stroke_dash_empty_rejected(self):
        drawing = self._base_stroke(dash=[])
        errors = list(DRAWING_VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_stroke_style_id(self):
        drawing = self._base_stroke(style_id="my_style")
        errors = list(DRAWING_VALIDATOR.iter_errors(drawing))
        self.assertEqual(errors, [])

    def test_stroke_invalid_style_id_rejected(self):
        drawing = self._base_stroke(style_id="bad style!")
        errors = list(DRAWING_VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)


# ---------------------------------------------------------------------------
# Drawing schema – holes / compound fill
# ---------------------------------------------------------------------------

class TestDrawingSchemaHoles(unittest.TestCase):
    def test_stroke_with_holes(self):
        drawing = {
            "id": "d1",
            "strokes": [
                {
                    "id": "s1",
                    "commands": [["M", 0, 0], ["L", 100, 0], ["L", 100, 100], ["Z"]],
                    "closed": True,
                    "fill": "#ff0000",
                    "fill_rule": "evenodd",
                    "holes": [
                        [["M", 20, 20], ["L", 80, 20], ["L", 80, 80], ["Z"]],
                    ],
                }
            ],
        }
        errors = list(DRAWING_VALIDATOR.iter_errors(drawing))
        self.assertEqual(errors, [])

    def test_stroke_holes_empty_array_rejected(self):
        drawing = {
            "id": "d1",
            "strokes": [
                {
                    "id": "s1",
                    "commands": [["M", 0, 0], ["L", 10, 10]],
                    "holes": [],
                }
            ],
        }
        errors = list(DRAWING_VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)

    def test_stroke_holes_invalid_path_rejected(self):
        drawing = {
            "id": "d1",
            "strokes": [
                {
                    "id": "s1",
                    "commands": [["M", 0, 0], ["L", 10, 10]],
                    "holes": [["not_a_command"]],
                }
            ],
        }
        errors = list(DRAWING_VALIDATOR.iter_errors(drawing))
        self.assertTrue(len(errors) > 0)


# ---------------------------------------------------------------------------
# Programmatic validation_service checks
# ---------------------------------------------------------------------------

class TestValidationServiceMilestoneB(unittest.TestCase):
    def _project_with_stroke(self, stroke_overrides):
        proj = _minimal_project()
        stroke = {"id": "s1", "points": [[0, 0], [10, 10]]}
        stroke.update(stroke_overrides)
        proj["drawings"] = {"d1": {"id": "d1", "strokes": [stroke]}}
        proj["scenes"][0]["layers"][0]["exposures"] = [{"start": 0, "length": 1, "drawing": "d1"}]
        return proj

    def test_valid_dash_passes(self):
        proj = self._project_with_stroke({"dash": [5, 3], "dash_offset": 1})
        errs = validate_project(proj)
        self.assertEqual(errs, [])

    def test_dash_zero_fails(self):
        proj = self._project_with_stroke({"dash": [5, 0]})
        errs = validate_project(proj)
        self.assertTrue(any("dash" in e for e in errs))

    def test_dash_negative_fails(self):
        proj = self._project_with_stroke({"dash": [-1, 5]})
        errs = validate_project(proj)
        self.assertTrue(any("dash" in e for e in errs))

    def test_dash_empty_fails(self):
        proj = self._project_with_stroke({"dash": []})
        errs = validate_project(proj)
        self.assertTrue(any("dash" in e for e in errs))

    def test_dash_too_long_fails(self):
        proj = self._project_with_stroke({"dash": list(range(1, 18))})
        errs = validate_project(proj)
        self.assertTrue(any("dash" in e for e in errs))

    def test_dash_offset_string_fails(self):
        proj = self._project_with_stroke({"dash_offset": "abc"})
        errs = validate_project(proj)
        self.assertTrue(any("dash_offset" in e for e in errs))

    def test_style_id_valid_passes(self):
        proj = self._project_with_stroke({"style_id": "my_style-01"})
        errs = validate_project(proj)
        self.assertEqual(errs, [])

    def test_style_id_invalid_fails(self):
        proj = self._project_with_stroke({"style_id": "bad style!"})
        errs = validate_project(proj)
        self.assertTrue(any("style_id" in e for e in errs))

    def test_holes_valid_passes(self):
        proj = self._project_with_stroke({
            "commands": [["M", 0, 0], ["L", 100, 0], ["L", 100, 100], ["Z"]],
            "holes": [[["M", 10, 10], ["L", 90, 10], ["L", 90, 90], ["Z"]]],
        })
        # remove points since we're using commands
        proj["drawings"]["d1"]["strokes"][0].pop("points", None)
        errs = validate_project(proj)
        self.assertEqual(errs, [])

    def test_holes_empty_fails(self):
        proj = self._project_with_stroke({
            "commands": [["M", 0, 0], ["L", 10, 10]],
            "holes": [],
        })
        proj["drawings"]["d1"]["strokes"][0].pop("points", None)
        errs = validate_project(proj)
        self.assertTrue(any("holes" in e for e in errs))

    def test_holes_invalid_path_fails(self):
        proj = self._project_with_stroke({
            "commands": [["M", 0, 0], ["L", 10, 10]],
            "holes": [["bad"]],
        })
        proj["drawings"]["d1"]["strokes"][0].pop("points", None)
        errs = validate_project(proj)
        self.assertTrue(any("holes" in e for e in errs))

    def test_character_part_stroke_accepts_new_fields(self):
        """Character part strokes should not reject dash/style_id/holes."""
        proj = _minimal_project()
        proj["characters"] = [
            {
                "format": "kae-character",
                "version": 1,
                "id": "char_01",
                "name": "TestChar",
                "parts": [
                    {
                        "id": "part_01",
                        "name": "head",
                        "strokes": [
                            {
                                "id": "cs1",
                                "points": [[0, 0], [10, 10]],
                                "dash": [5, 3],
                                "dash_offset": 1,
                                "style_id": "sty1",
                                "fill_rule": "evenodd",
                                "line_cap": "butt",
                                "line_join": "miter",
                            }
                        ],
                    }
                ],
            }
        ]
        errs = validate_project(proj)
        self.assertEqual(errs, [])


if __name__ == "__main__":
    unittest.main()
