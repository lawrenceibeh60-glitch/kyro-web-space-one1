"""Milestone C: Scene hierarchy, group layers, transform composition, cycle detection.

Validates scene.schema.json with group layer type, recursive children,
programmatic validation_service checks for hierarchy, cycles, and visibility.
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
        "id": "proj_01",
        "name": "Test",
        "settings": {"fps": 24, "duration_frames": 10, "width": 800, "height": 600},
        "scenes": [{"id": "scene_01", "layers": [{"id": "layer_01", "type": "drawing"}]}],
        "drawings": {},
    }


class TestSceneSchemaGroupLayers(unittest.TestCase):
    """JSON Schema validation for group layer type."""

    def test_valid_group_layer(self):
        scene = {
            "id": "sc1",
            "layers": [
                {
                    "id": "grp1",
                    "type": "group",
                    "children": [
                        {"id": "child1", "type": "drawing"}
                    ],
                }
            ],
        }
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])

    def test_nested_groups(self):
        scene = {
            "id": "sc1",
            "layers": [
                {
                    "id": "grp1",
                    "type": "group",
                    "children": [
                        {
                            "id": "grp2",
                            "type": "group",
                            "children": [
                                {"id": "leaf", "type": "drawing"}
                            ],
                        }
                    ],
                }
            ],
        }
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])

    def test_group_with_transform(self):
        scene = {
            "id": "sc1",
            "layers": [
                {
                    "id": "grp1",
                    "type": "group",
                    "transform": {"x": 10, "y": 20, "rotation": 45, "scale_x": 2, "scale_y": 2},
                    "children": [
                        {"id": "child1", "type": "drawing"}
                    ],
                }
            ],
        }
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])

    def test_invalid_type_rejected(self):
        scene = {
            "id": "sc1",
            "layers": [
                {"id": "ly1", "type": "unknown_type"}
            ],
        }
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertTrue(len(errors) > 0)

    def test_drawing_backward_compat(self):
        scene = {
            "id": "sc1",
            "layers": [
                {"id": "ly1", "type": "drawing", "visible": True, "opacity": 1}
            ],
        }
        errors = list(VALIDATOR.iter_errors(scene))
        self.assertEqual(errors, [])


class TestValidationServiceHierarchy(unittest.TestCase):
    """Programmatic validation for scene hierarchy."""

    def test_flat_drawing_still_valid(self):
        proj = _minimal_project()
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertEqual(errs, [])

    def test_group_layer_accepted(self):
        proj = _minimal_project()
        proj["scenes"][0]["layers"] = [
            {
                "id": "grp1",
                "type": "group",
                "children": [
                    {"id": "child1", "type": "drawing"}
                ],
            }
        ]
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertEqual(errs, [])

    def test_nested_groups_accepted(self):
        proj = _minimal_project()
        proj["scenes"][0]["layers"] = [
            {
                "id": "grp1",
                "type": "group",
                "children": [
                    {
                        "id": "grp2",
                        "type": "group",
                        "children": [
                            {"id": "leaf1", "type": "drawing"}
                        ],
                    }
                ],
            }
        ]
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertEqual(errs, [])

    def test_duplicate_id_across_hierarchy_rejected(self):
        proj = _minimal_project()
        proj["scenes"][0]["layers"] = [
            {
                "id": "grp1",
                "type": "group",
                "children": [
                    {"id": "grp1", "type": "drawing"}
                ],
            }
        ]
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertTrue(any("duplicate" in e for e in errs))

    def test_cycle_detection_direct_parent(self):
        """A child referencing its parent's ID creates a cycle."""
        proj = _minimal_project()
        proj["scenes"][0]["layers"] = [
            {
                "id": "grp1",
                "type": "group",
                "children": [
                    {
                        "id": "grp2",
                        "type": "group",
                        "children": [
                            {"id": "grp1", "type": "drawing"}
                        ],
                    }
                ],
            }
        ]
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertTrue(any("duplicate" in e or "cycle" in e.lower() for e in errs))

    def test_invalid_type_rejected(self):
        proj = _minimal_project()
        proj["scenes"][0]["layers"] = [
            {"id": "ly1", "type": "invalid_type"}
        ]
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertTrue(any("type" in e for e in errs))

    def test_group_depth_validated(self):
        proj = _minimal_project()
        proj["scenes"][0]["layers"] = [
            {
                "id": "grp1",
                "type": "group",
                "depth": 5,
                "children": [
                    {"id": "child1", "type": "drawing"}
                ],
            }
        ]
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertTrue(any("depth" in e for e in errs))

    def test_group_opacity_validated(self):
        proj = _minimal_project()
        proj["scenes"][0]["layers"] = [
            {
                "id": "grp1",
                "type": "group",
                "opacity": 2.0,
                "children": [
                    {"id": "child1", "type": "drawing"}
                ],
            }
        ]
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertTrue(any("opacity" in e for e in errs))

    def test_child_exposure_validated(self):
        proj = _minimal_project()
        proj["drawings"] = {"d1": {"id": "d1", "strokes": []}}
        proj["scenes"][0]["layers"] = [
            {
                "id": "grp1",
                "type": "group",
                "children": [
                    {
                        "id": "child1",
                        "type": "drawing",
                        "exposures": [{"start": 0, "length": 1, "drawing": "d1"}],
                    }
                ],
            }
        ]
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertEqual(errs, [])

    def test_child_exposure_missing_drawing_rejected(self):
        proj = _minimal_project()
        proj["scenes"][0]["layers"] = [
            {
                "id": "grp1",
                "type": "group",
                "children": [
                    {
                        "id": "child1",
                        "type": "drawing",
                        "exposures": [{"start": 0, "length": 1, "drawing": "nonexistent"}],
                    }
                ],
            }
        ]
        from backend.services.validation_service import validate_project
        errs = validate_project(proj)
        self.assertTrue(any("does not exist" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
