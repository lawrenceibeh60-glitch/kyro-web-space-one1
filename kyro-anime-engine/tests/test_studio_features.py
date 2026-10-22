import io
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from werkzeug.datastructures import FileStorage

import config
from backend.app.exceptions import ApiError
from backend.app.application import create_app
from backend.services import audio_service, character_service, render_service, rig_service
from backend.services.validation_service import validate_character_document, validate_project


class StudioFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).parents[1]
        cls.project = json.loads((root / "formats/examples/project.json").read_text(encoding="utf-8"))
        cls.character = json.loads((root / "formats/examples/character.json").read_text(encoding="utf-8"))

    def test_generator_creates_editable_parts_and_updates_stable_id(self):
        project = deepcopy(self.project)
        options = {
            "id": "generated_hero", "name": "Generated Hero",
            "hairstyle": "twin_tails", "expression": "determined",
            "hair_color": "#203050", "eye_color": "#225588",
            "skin_color": "#efc6a6", "outfit_color": "#893f72",
        }
        with patch.object(character_service.repo, "load", return_value=project), \
             patch.object(character_service.repo, "save") as save:
            first = character_service.generate_character(project["id"], options)
            updated_options = {**options, "name": "Updated Hero", "hairstyle": "long"}
            second = character_service.generate_character(project["id"], updated_options)

        self.assertEqual(validate_character_document(second["character"]), [])
        self.assertEqual(validate_project(second["project"]), [])
        self.assertEqual(len(second["project"]["characters"]), 1)
        self.assertEqual(second["character"]["name"], "Updated Hero")
        self.assertEqual(
            [part["id"] for part in first["character"]["parts"]],
            [part["id"] for part in second["character"]["parts"]],
        )
        self.assertEqual(save.call_count, 2)

    def test_effect_api_service_upserts_by_id(self):
        project = deepcopy(self.project)
        with patch.object(render_service.repo, "load", return_value=project), \
             patch.object(render_service.repo, "save") as save:
            first = render_service.add_effect(project["id"], {
                "id": "fx_flash", "type": "lightning", "scene_id": "scene_1",
            })
            updated = render_service.add_effect(project["id"], {
                "id": "fx_flash", "type": "speed_lines", "scene_id": "scene_1",
                "count": 48, "intensity": 0.8,
            })

        self.assertEqual(first["type"], "lightning")
        self.assertEqual(updated["type"], "speed_lines")
        self.assertEqual(len(project["effects"]), 1)
        self.assertEqual(validate_project(project), [])
        self.assertEqual(save.call_count, 2)

    def test_glow_and_impact_flash_effects_validate_as_native_scene_effects(self):
        project = deepcopy(self.project)
        project["effects"] = [
            {"id": "fx_glow", "scene_id": "scene_1", "type": "glow",
             "enabled": True, "start_frame": 0, "end_frame": 12,
             "intensity": 0.65, "color": "#ffffff", "speed": 1},
            {"id": "fx_impact", "scene_id": "scene_1", "type": "impact_flash",
             "enabled": True, "start_frame": 4, "end_frame": 10,
             "intensity": 0.8, "color": "#ffcc66", "speed": 1.5},
        ]
        self.assertEqual(validate_project(project), [])

        project["effects"][0]["type"] = "unknown_effect"
        self.assertTrue(any("unsupported effect" in error for error in validate_project(project)))

    def test_soft_shadow_and_depth_of_field_effects_validate(self):
        project = deepcopy(self.project)
        project["effects"] = [
            {"id": "fx_shadow", "scene_id": "scene_1", "type": "soft_shadow",
             "intensity": 0.6, "speed": 8, "color": "#111827"},
            {"id": "fx_dof", "scene_id": "scene_1", "type": "depth_of_field",
             "intensity": 0.75, "focus_depth": 0.45, "range": 0.3},
        ]
        self.assertEqual(validate_project(project), [])
        project["effects"][1]["range"] = 0
        self.assertTrue(any("range: number >0..1 required" in error for error in validate_project(project)))

    def test_rig_validates_character_part_links_and_rejects_cycles(self):
        project = deepcopy(self.project)
        with patch.object(character_service.repo, "load", return_value=project), \
             patch.object(character_service.repo, "save"):
            character_service.import_character(project["id"], deepcopy(self.character))
        with patch.object(rig_service.repo, "load", return_value=project), \
             patch.object(rig_service.repo, "save") as save:
            rig = rig_service.save_rig(project["id"], {
                "id": "hero_rig", "name": "Hero Rig", "character_id": self.character["id"],
                "bones": [
                    {"id": "body_bone", "name": "Body", "character_part_id": "body",
                     "pivot": {"x": 640, "y": 360}},
                    {"id": "head_bone", "name": "Head", "parent_id": "body_bone",
                     "character_part_id": "head", "pivot": {"x": 640, "y": 250}},
                ],
            })
            self.assertEqual(rig["id"], "hero_rig")
            self.assertEqual(validate_project(project), [])
            with self.assertRaises(ApiError):
                rig_service.save_rig(project["id"], {
                    **rig,
                    "bones": [
                        {**rig["bones"][0], "parent_id": "head_bone"},
                        rig["bones"][1],
                    ],
                })

        self.assertEqual(save.call_count, 1)
        self.assertNotIn("parent_id", project["rigs"][0]["bones"][0])

    def test_character_update_removes_stale_bones_and_reparents_children(self):
        project = deepcopy(self.project)
        character = deepcopy(self.character)
        with patch.object(character_service.repo, "load", return_value=project), \
             patch.object(character_service.repo, "save"):
            character_service.import_character(project["id"], character)
            rig_service.save_rig(project["id"], {
                "id": "hero_rig", "name": "Hero Rig", "character_id": character["id"],
                "bones": [
                    {"id": "body_bone", "name": "Body", "character_part_id": "body",
                     "pivot": {"x": 640, "y": 360}},
                    {"id": "head_bone", "name": "Head", "parent_id": "body_bone",
                     "character_part_id": "head", "pivot": {"x": 640, "y": 250}},
                ],
            })
            update = deepcopy(character)
            update["parts"] = [part for part in update["parts"] if part["id"] == "body"]
            character_service.import_character(project["id"], update)

        self.assertEqual([bone["id"] for bone in project["rigs"][0]["bones"]], ["body_bone"])
        self.assertEqual(validate_project(project), [])

    def test_audio_upload_stores_project_scoped_data_and_metadata(self):
        project = deepcopy(self.project)
        upload = FileStorage(
            stream=io.BytesIO(b"test audio"),
            filename="voice.wav",
            content_type="audio/wav",
        )
        with tempfile.TemporaryDirectory() as temp_dir, \
             patch.object(config, "PROJECTS_DIR", Path(temp_dir)), \
             patch.object(audio_service.repo, "load", return_value=project), \
             patch.object(audio_service.repo, "save") as save:
            result = audio_service.upload_audio(project["id"], upload, {
                "id": "voice_main", "name": "Voice", "start_frame": "6",
                "offset_seconds": "0.25", "volume": "0.8",
            })
            path, mime, name = audio_service.audio_file(project["id"], "voice_main")

            self.assertEqual(path.read_bytes(), b"test audio")
            self.assertEqual(mime, "audio/wav")
            self.assertEqual(name, "Voice")
            self.assertEqual(result["clip"]["start_frame"], 6)
            self.assertEqual(result["clip"]["offset_seconds"], 0.25)
            self.assertEqual(validate_project(project), [])
            save.assert_called_once()

    def test_audio_rejects_unsupported_extensions(self):
        upload = FileStorage(stream=io.BytesIO(b"not audio"), filename="voice.exe")
        with patch.object(audio_service.repo, "load", return_value=deepcopy(self.project)):
            with self.assertRaises(ApiError) as raised:
                audio_service.upload_audio(self.project["id"], upload, {})
        self.assertEqual(raised.exception.status, 415)

    def test_generator_and_effect_routes_are_wired(self):
        project = deepcopy(self.project)
        app = create_app()
        with patch.object(character_service.repo, "load", return_value=project), \
             patch.object(character_service.repo, "save"), \
             patch.object(render_service.repo, "load", return_value=project), \
             patch.object(render_service.repo, "save"):
            client = app.test_client()
            generated = client.post(
                f"/api/projects/{project['id']}/characters/generate",
                json={"id": "api_hero", "name": "API Hero"},
            )
            effect = client.post(
                f"/api/projects/{project['id']}/effects",
                json={"id": "fx_api", "scene_id": "scene_1", "type": "particles"},
            )

        self.assertEqual(generated.status_code, 201)
        self.assertEqual(generated.get_json()["character"]["id"], "api_hero")
        self.assertEqual(effect.status_code, 201)
        self.assertEqual(effect.get_json()["id"], "fx_api")

    def test_audio_upload_and_download_routes_are_wired(self):
        project = deepcopy(self.project)
        app = create_app()
        with tempfile.TemporaryDirectory() as temp_dir, \
             patch.object(config, "PROJECTS_DIR", Path(temp_dir)), \
             patch.object(audio_service.repo, "load", return_value=project), \
             patch.object(audio_service.repo, "save"):
            client = app.test_client()
            upload = client.post(
                f"/api/projects/{project['id']}/audio",
                data={
                    "id": "api_voice",
                    "name": "API voice",
                    "start_frame": "2",
                    "offset_seconds": "0",
                    "volume": "1",
                    "file": (io.BytesIO(b"wave data"), "voice.wav", "audio/wav"),
                },
                content_type="multipart/form-data",
            )
            downloaded = client.get(f"/api/projects/{project['id']}/audio/api_voice")
            downloaded_data = downloaded.data
            downloaded.close()

        self.assertEqual(upload.status_code, 201)
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded_data, b"wave data")


if __name__ == "__main__":
    unittest.main()
