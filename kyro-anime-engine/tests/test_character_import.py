import json
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from backend.app.exceptions import ApiError
from backend.app.application import create_app
from backend.services import character_service
from backend.services.validation_service import validate_character_document, validate_project


class CharacterImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parents[1]
        cls.project = json.loads((root / "formats/examples/project.json").read_text(encoding="utf-8"))
        cls.character = json.loads((root / "formats/examples/character.json").read_text(encoding="utf-8"))

    def test_example_character_document_is_valid(self):
        self.assertEqual(validate_character_document(self.character), [])

    def test_import_creates_persistent_part_layers_and_registry_entry(self):
        project = deepcopy(self.project)
        with patch.object(character_service.repo, "load", return_value=project), \
             patch.object(character_service.repo, "save") as save:
            result = character_service.import_character(project["id"], deepcopy(self.character))

        imported = result["project"]
        self.assertEqual(len(imported["characters"]), 1)
        self.assertEqual(imported["characters"][0]["id"], "sample_hero")
        layers = [layer for layer in imported["scenes"][0]["layers"]
                  if layer.get("character_id") == "sample_hero"]
        self.assertEqual(len(layers), len(self.character["parts"]))
        self.assertEqual(layers[0]["id"], "chlayer_sample_hero_body")
        self.assertEqual(layers[0]["exposures"][0]["drawing"], "chdraw_sample_hero_body")
        self.assertEqual(validate_project(imported), [])
        save.assert_called_once()

    def test_reimport_updates_art_but_preserves_part_ids_and_animation(self):
        project = deepcopy(self.project)
        first = deepcopy(self.character)
        first["parts"] = [first["parts"][0]]
        first["parts"][0]["tracks"] = {
            "rotation": [{"t": 0, "v": 0}, {"t": 8, "v": 30}]
        }
        with patch.object(character_service.repo, "load", side_effect=lambda _pid: deepcopy(project)), \
             patch.object(character_service.repo, "save") as save:
            first_result = character_service.import_character(project["id"], first)
            project = first_result["project"]
            second = deepcopy(first)
            second["name"] = "Updated Hero"
            second["parts"][0].pop("tracks")
            second["parts"][0]["strokes"][0]["fill"] = "#cc3344"
            second_result = character_service.import_character(project["id"], second)

        updated = second_result["project"]
        layers = [layer for layer in updated["scenes"][0]["layers"]
                  if layer.get("character_id") == "sample_hero"]
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers[0]["id"], "chlayer_sample_hero_body")
        self.assertEqual(layers[0]["tracks"]["rotation"][1]["v"], 30)
        self.assertEqual(updated["drawings"]["chdraw_sample_hero_body"]["strokes"][0]["fill"], "#cc3344")
        self.assertEqual(len(updated["characters"]), 1)
        self.assertEqual(updated["characters"][0]["name"], "Updated Hero")
        self.assertEqual(save.call_count, 2)
        self.assertEqual(validate_project(updated), [])

    def test_generated_character_has_separate_articulated_limb_parts(self):
        project = deepcopy(self.project)
        options = {
            "id": "articulated_hero",
            "name": "Articulated Hero",
            "hairstyle": "long",
            "expression": "determined",
        }
        with patch.object(character_service.repo, "load", return_value=project), \
             patch.object(character_service.repo, "save"):
            result = character_service.generate_character(project["id"], options)

        character = result["character"]
        part_ids = {part["id"] for part in character["parts"]}
        expected = {
            "left_thigh", "left_shin", "left_foot",
            "right_thigh", "right_shin", "right_foot",
            "arm_left", "forearm_left", "hand_left",
            "arm_right", "forearm_right", "hand_right",
            "neck", "body", "head", "hair_back", "hair_front",
        }
        self.assertTrue(expected.issubset(part_ids))
        self.assertNotIn("legs", part_ids)
        self.assertTrue(all(part["strokes"] for part in character["parts"]))
        strokes_by_part = {
            part["id"]: {stroke["id"] for stroke in part["strokes"]}
            for part in character["parts"]
        }
        self.assertTrue({"hair-sheen-left", "hair-sheen-right"}.issubset(strokes_by_part["hair_back"]))
        self.assertIn("fringe-highlight", strokes_by_part["hair_front"])
        self.assertTrue({"jacket-center-seam", "jacket-button-top", "jacket-button-mid", "jacket-button-low"}
                        .issubset(strokes_by_part["body"]))
        self.assertIn("left-shoe-sole", strokes_by_part["left_foot"])
        self.assertIn("right-shoe-lace", strokes_by_part["right_foot"])
        self.assertEqual(validate_character_document(character), [])

    def test_import_api_persists_and_returns_updated_project(self):
        project = deepcopy(self.project)
        app = create_app()
        with patch.object(character_service.repo, "load", return_value=project), \
             patch.object(character_service.repo, "save"):
            response = app.test_client().post(
                f"/api/projects/{project['id']}/characters/import",
                json=self.character,
            )

        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body["character"]["id"], "sample_hero")
        self.assertIn("characters", body["project"])
        self.assertEqual(validate_project(body["project"]), [])

    def test_character_can_target_a_scene_and_remove_a_part_on_update(self):
        project = deepcopy(self.project)
        project["scenes"].append({"id": "scene_2", "name": "Scene 2", "layers": []})
        character = deepcopy(self.character)
        character["scene_id"] = "scene_2"
        with patch.object(character_service.repo, "load", side_effect=lambda _pid: deepcopy(project)), \
             patch.object(character_service.repo, "save"):
            first_result = character_service.import_character(project["id"], character)
            project = first_result["project"]
            update = deepcopy(character)
            update["parts"] = [update["parts"][0]]
            second_result = character_service.import_character(project["id"], update)

        updated = second_result["project"]
        self.assertFalse(any(
            layer.get("character_id") == "sample_hero"
            for layer in updated["scenes"][0]["layers"]
        ))
        self.assertEqual(
            [layer["character_part_id"] for layer in updated["scenes"][1]["layers"]
             if layer.get("character_id") == "sample_hero"],
            ["body"],
        )
        self.assertNotIn("chdraw_sample_hero_head", updated["drawings"])
        self.assertEqual(validate_project(updated), [])

    def test_invalid_character_does_not_write_project(self):
        project = deepcopy(self.project)
        invalid = deepcopy(self.character)
        invalid["parts"][0]["strokes"][0]["points"] = []
        with patch.object(character_service.repo, "load", return_value=project), \
             patch.object(character_service.repo, "save") as save:
            with self.assertRaises(ApiError):
                character_service.import_character(project["id"], invalid)
        save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
