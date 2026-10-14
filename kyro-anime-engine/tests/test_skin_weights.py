import unittest
from unittest.mock import patch

from backend.services.project_service import create_project, repo
from backend.services.validation_service import validate_project


def skinned_project():
    with patch.object(repo, "save"):
        project = create_project("Skin weights test")
    project["drawings"]["skin_drawing"] = {
        "id": "skin_drawing",
        "strokes": [{
            "id": "skin_stroke",
            "points": [[10, 0, 1], [0, 10, 1]],
            "skin_weights": [
                [{"bone_id": "body_bone", "weight": 1}],
                [{"bone_id": "body_bone", "weight": 1}],
            ],
        }],
    }
    project["characters"] = [{
        "format": "kae-character",
        "version": 1,
        "id": "skin_character",
        "name": "Skin Character",
        "parts": [{"id": "body", "name": "Body", "strokes": []}],
    }]
    project["rigs"] = [{
        "id": "skin_rig",
        "name": "Skin Rig",
        "character_id": "skin_character",
        "bones": [{
            "id": "body_bone",
            "name": "Body",
            "character_part_id": "body",
            "pivot": {"x": 0, "y": 0},
        }],
    }]
    layer = project["scenes"][0]["layers"][0]
    layer["character_id"] = "skin_character"
    layer["character_part_id"] = "body"
    layer["exposures"] = [{"start": 0, "length": 24, "drawing": "skin_drawing"}]
    return project


class SkinWeightValidationTests(unittest.TestCase):
    def test_valid_per_point_skin_weights_are_accepted(self):
        self.assertEqual(validate_project(skinned_project()), [])

    def test_skin_weights_must_match_point_count(self):
        project = skinned_project()
        project["drawings"]["skin_drawing"]["strokes"][0]["skin_weights"].pop()
        errors = validate_project(project)
        self.assertTrue(any("one influence list per point" in error for error in errors))

    def test_skin_weights_must_reference_an_existing_rig_bone(self):
        project = skinned_project()
        project["drawings"]["skin_drawing"]["strokes"][0]["skin_weights"][0][0]["bone_id"] = "missing_bone"
        errors = validate_project(project)
        self.assertTrue(any("rig bone not found" in error for error in errors))

    def test_skin_weights_cannot_exceed_one_or_be_empty(self):
        project = skinned_project()
        weights = project["drawings"]["skin_drawing"]["strokes"][0]["skin_weights"]
        weights[0] = [
            {"bone_id": "body_bone", "weight": 0.8},
            {"bone_id": "other_bone", "weight": 0.8},
        ]
        weights[1] = []
        errors = validate_project(project)
        self.assertTrue(any("weights must sum" in error for error in errors))
        self.assertTrue(any("non-empty influence list" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
