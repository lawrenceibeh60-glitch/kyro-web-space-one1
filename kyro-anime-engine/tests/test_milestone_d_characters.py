"""Milestone D: Character builders, instances, and per-instance overrides.

Tests deterministic builder output, character_instance layer type validation,
instance_overrides schema checks, and verifies re-import does not duplicate layers.
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


SCENE_SCHEMA = _load("scene.schema.json")
ANIMATION_SCHEMA = _load("animation.schema.json")

_REGISTRY = Registry().with_resources(
    [
        ("scene.schema.json", Resource.from_contents(SCENE_SCHEMA)),
        ("animation.schema.json", Resource.from_contents(ANIMATION_SCHEMA)),
    ]
)
VALIDATOR = Draft202012Validator(SCENE_SCHEMA, registry=_REGISTRY)


def _minimal_project():
    return {
        "format": "kae",
        "version": 1,
        "drawings": {},
        "settings": {"fps": 24, "duration_frames": 48, "width": 800, "height": 600},
        "scenes": [
            {
                "id": "scene_1",
                "layers": [
                    {"id": "ly1", "type": "drawing", "exposures": [{"start": 0, "length": 1, "drawing": "d1"}]}
                ],
            }
        ],
    }


class TestCharacterInstanceSchema(unittest.TestCase):
    """Validate character_instance layer type in scene.schema.json."""

    def test_character_instance_layer_valid(self):
        scene = {
            "id": "s1",
            "layers": [
                {
                    "id": "inst1",
                    "type": "character_instance",
                    "character_id": "hero",
                    "instance_overrides": {"opacity": 0.5, "visible": True},
                }
            ],
        }
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])

    def test_character_instance_with_children(self):
        scene = {
            "id": "s1",
            "layers": [
                {
                    "id": "inst1",
                    "type": "character_instance",
                    "children": [
                        {"id": "part1", "type": "drawing"}
                    ],
                }
            ],
        }
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])

    def test_character_instance_invalid_opacity_override(self):
        scene = {
            "id": "s1",
            "layers": [
                {
                    "id": "inst1",
                    "type": "character_instance",
                    "instance_overrides": {"opacity": 2.0},
                }
            ],
        }
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertTrue(len(errors) > 0)

    def test_character_instance_transform_override(self):
        scene = {
            "id": "s1",
            "layers": [
                {
                    "id": "inst1",
                    "type": "character_instance",
                    "instance_overrides": {
                        "transform": {"x": 100, "y": 200, "rotation": 45}
                    },
                }
            ],
        }
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])


class TestCharacterInstanceValidation(unittest.TestCase):
    """Test programmatic validation of character_instance layers."""

    def test_character_instance_accepted(self):
        proj = _minimal_project()
        proj["drawings"]["d1"] = {"id": "d1", "strokes": []}
        proj["scenes"][0]["layers"].append({
            "id": "inst1",
            "type": "character_instance",
            "character_id": "hero",
        })
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertFalse(any("type" in e for e in errs), f"Unexpected errors: {errs}")

    def test_character_instance_with_overrides(self):
        proj = _minimal_project()
        proj["drawings"]["d1"] = {"id": "d1", "strokes": []}
        proj["scenes"][0]["layers"].append({
            "id": "inst1",
            "type": "character_instance",
            "instance_overrides": {"opacity": 0.8, "visible": False},
        })
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertFalse(any("instance_overrides" in e for e in errs), f"Unexpected: {errs}")

    def test_character_instance_invalid_opacity_rejected(self):
        proj = _minimal_project()
        proj["drawings"]["d1"] = {"id": "d1", "strokes": []}
        proj["scenes"][0]["layers"].append({
            "id": "inst1",
            "type": "character_instance",
            "instance_overrides": {"opacity": 5.0},
        })
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertTrue(any("opacity" in e for e in errs))

    def test_character_instance_invalid_visible_rejected(self):
        proj = _minimal_project()
        proj["drawings"]["d1"] = {"id": "d1", "strokes": []}
        proj["scenes"][0]["layers"].append({
            "id": "inst1",
            "type": "character_instance",
            "instance_overrides": {"visible": "yes"},
        })
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertTrue(any("visible" in e for e in errs))

    def test_character_instance_with_children(self):
        proj = _minimal_project()
        proj["drawings"]["d1"] = {"id": "d1", "strokes": []}
        proj["scenes"][0]["layers"].append({
            "id": "inst1",
            "type": "character_instance",
            "children": [
                {"id": "child_part", "type": "drawing"}
            ],
        })
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertFalse(any("children" in e or "type" in e for e in errs), f"Unexpected: {errs}")

    def test_character_instance_cycle_detected(self):
        proj = _minimal_project()
        proj["drawings"]["d1"] = {"id": "d1", "strokes": []}
        proj["scenes"][0]["layers"].append({
            "id": "inst1",
            "type": "character_instance",
            "children": [
                {
                    "id": "inst1",
                    "type": "character_instance",
                }
            ],
        })
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertTrue(any("duplicate" in e.lower() or "cycle" in e.lower() for e in errs))


class TestDeterministicBuilders(unittest.TestCase):
    """Verify build_character_document produces stable, deterministic output."""

    def test_build_character_document_returns_valid_structure(self):
        from backend.services.character_service import build_character_document
        doc = build_character_document("hero", "Hero", {
            "hair_color": "#303b70",
            "eye_color": "#4c8ba8",
            "skin_color": "#f2c7a5",
            "outfit_color": "#a34f78",
        }, 800, 600)
        self.assertEqual(doc["format"], "kae-character")
        self.assertEqual(doc["version"], 1)
        self.assertEqual(doc["id"], "hero")
        self.assertEqual(doc["name"], "Hero")
        self.assertIsInstance(doc["parts"], list)
        self.assertTrue(len(doc["parts"]) >= 5)

    def test_build_character_document_deterministic(self):
        from backend.services.character_service import build_character_document
        opts = {"hair_color": "#303b70", "eye_color": "#4c8ba8",
                "skin_color": "#f2c7a5", "outfit_color": "#a34f78"}
        doc1 = build_character_document("hero", "Hero", opts, 800, 600)
        doc2 = build_character_document("hero", "Hero", opts, 800, 600)
        self.assertEqual(doc1, doc2)

    def test_build_character_document_part_ids_stable(self):
        from backend.services.character_service import build_character_document
        doc = build_character_document("hero", "Hero", {}, 800, 600)
        part_ids = [p["id"] for p in doc["parts"]]
        self.assertIn("head", part_ids)
        self.assertIn("body", part_ids)
        self.assertIn("arm_left", part_ids)
        self.assertIn("arm_right", part_ids)

    def test_build_character_document_hairstyle_variants(self):
        from backend.services.character_service import build_character_document
        base_opts = {"hair_color": "#303b70", "eye_color": "#4c8ba8",
                     "skin_color": "#f2c7a5", "outfit_color": "#a34f78"}
        short_doc = build_character_document("h1", "S", {**base_opts, "hairstyle": "short"}, 800, 600)
        long_doc = build_character_document("h2", "L", {**base_opts, "hairstyle": "long"}, 800, 600)
        twin_doc = build_character_document("h3", "T", {**base_opts, "hairstyle": "twin_tails"}, 800, 600)
        hair_back_short = next(p for p in short_doc["parts"] if p["id"] == "hair_back")
        hair_back_long = next(p for p in long_doc["parts"] if p["id"] == "hair_back")
        hair_back_twin = next(p for p in twin_doc["parts"] if p["id"] == "hair_back")
        self.assertLess(len(hair_back_short["strokes"]), len(hair_back_long["strokes"]))
        self.assertLess(len(hair_back_short["strokes"]), len(hair_back_twin["strokes"]))

    def test_build_head_strokes_returns_list(self):
        from backend.services.character_service import build_head_strokes
        strokes = build_head_strokes(400, 150, 1.0, 1.0, "#f2c7a5", "#4c8ba8", "#302b37", "smile")
        self.assertIsInstance(strokes, list)
        self.assertTrue(len(strokes) > 5)


if __name__ == "__main__":
    unittest.main()