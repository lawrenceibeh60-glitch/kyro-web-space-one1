import json
import unittest
from copy import deepcopy
from pathlib import Path

from backend.services.validation_service import validate_character_document, validate_project


class DrawingPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parents[1]
        cls.project = json.loads((root / "formats/examples/project.json").read_text(encoding="utf-8"))
        cls.character = json.loads((root / "formats/examples/character.json").read_text(encoding="utf-8"))

    @staticmethod
    def path_stroke():
        return {
            "id": "curve",
            "color": "#223344",
            "width": 3,
            "fill": "#aabbcc",
            "commands": [
                ["M", 10, 20],
                ["Q", 20, 0, 30, 20],
                ["C", 35, 30, 45, 30, 50, 20],
                ["L", 50, 50],
                ["Z"],
            ],
        }

    def test_project_accepts_quadratic_and_cubic_path_strokes(self):
        project = deepcopy(self.project)
        project["drawings"]["d_ball_round"]["strokes"] = [self.path_stroke()]
        self.assertEqual(validate_project(project), [])

    def test_character_parts_accept_path_strokes(self):
        character = deepcopy(self.character)
        character["parts"][0]["strokes"] = [self.path_stroke()]
        self.assertEqual(validate_character_document(character), [])

    def test_path_commands_require_valid_order_and_coordinates(self):
        project = deepcopy(self.project)
        project["drawings"]["d_ball_round"]["strokes"] = [{
            "id": "bad_path",
            "commands": [["L", 0, 0], ["Q", 1, 2, float("nan"), 4]],
        }]
        errors = validate_project(project)
        self.assertTrue(any("must begin with M" in error for error in errors))
        self.assertTrue(any("finite numbers" in error for error in errors))

    def test_stroke_requires_exactly_one_geometry_representation(self):
        project = deepcopy(self.project)
        stroke = self.path_stroke()
        stroke["points"] = [[0, 0], [1, 1]]
        project["drawings"]["d_ball_round"]["strokes"] = [stroke]
        errors = validate_project(project)
        self.assertTrue(any("exactly one of points or commands" in error for error in errors))

    def test_path_command_arity_is_validated(self):
        project = deepcopy(self.project)
        project["drawings"]["d_ball_round"]["strokes"] = [{
            "id": "bad_arity",
            "commands": [["M", 0, 0], ["C", 1, 2, 3, 4]],
        }]
        errors = validate_project(project)
        self.assertTrue(any("C command requires 6 coordinates" in error for error in errors))

    def test_path_schema_requires_exact_command_tuple_lengths(self):
        root = Path(__file__).parents[1]
        schema = json.loads((root / "formats/schemas/drawing.schema.json").read_text(encoding="utf-8"))
        path_schema = json.loads((root / "formats/schemas/path.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(
            schema["$defs"]["stroke"]["properties"]["commands"]["$ref"],
            "path.schema.json#/$defs/path",
        )
        variants = path_schema["$defs"]["segment"]["oneOf"]
        tuple_schemas = [path_schema["$defs"]["move"], *[
            tuple_schema for variant in variants
            for tuple_schema in (variant["oneOf"] if "oneOf" in variant else [variant])
        ]]
        for tuple_schema in tuple_schemas:
            arity = len(tuple_schema["prefixItems"])
            self.assertEqual(tuple_schema["minItems"], arity)
            self.assertEqual(tuple_schema["maxItems"], arity)

    def test_stroke_line_style_values_are_validated(self):
        project = deepcopy(self.project)
        stroke = self.path_stroke()
        stroke.update(line_cap=[], line_join="sharp", fill_rule="positive")
        project["drawings"]["d_ball_round"]["strokes"] = [stroke]
        errors = validate_project(project)
        for field in ("line_cap", "line_join", "fill_rule"):
            self.assertTrue(any(f".{field}: unsupported value" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
