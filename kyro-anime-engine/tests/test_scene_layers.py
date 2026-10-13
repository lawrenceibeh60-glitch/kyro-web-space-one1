import unittest
from copy import deepcopy
from unittest.mock import patch

from backend.services import project_service, scene_service


class SceneLayerPersistenceTests(unittest.TestCase):
    def test_layer_mutations_are_saved_to_the_project_state(self):
        with patch.object(project_service.repo, "save"):
            project = project_service.create_project("Scene layer test")

        current = deepcopy(project)

        def fake_load(_pid):
            return deepcopy(current)

        def fake_save(_pid, data):
            current.clear()
            current.update(deepcopy(data))

        with patch.object(scene_service.repo, "load", side_effect=fake_load), \
             patch.object(scene_service.repo, "save", side_effect=fake_save):
            created = scene_service.add_layer("project_1", "scene_1", {"id": "layer_2", "name": "Layer 2"})
            self.assertEqual(created["id"], "layer_2")
            self.assertEqual(current["scenes"][0]["layers"][1]["id"], "layer_2")

            updated = scene_service.update_layer("project_1", "scene_1", "layer_2", {"name": "Layer 2 updated"})
            self.assertEqual(updated["name"], "Layer 2 updated")
            self.assertEqual(current["scenes"][0]["layers"][1]["name"], "Layer 2 updated")

            scene_service.delete_layer("project_1", "scene_1", "layer_2")
            self.assertEqual(len(current["scenes"][0]["layers"]), 1)


if __name__ == "__main__":
    unittest.main()
