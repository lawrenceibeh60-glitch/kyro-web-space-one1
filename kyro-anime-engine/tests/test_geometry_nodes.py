import json
import unittest
from pathlib import Path

from backend.services.validation_service import validate_project

ROOT = Path(__file__).resolve().parents[1]


class GeometryNodeValidationTests(unittest.TestCase):
    def project(self):
        return json.loads((ROOT / "formats" / "examples" / "project.json").read_text(encoding="utf-8"))

    def graph(self):
        return {
            "id": "graph_main", "name": "Main Geometry",
            "nodes": [
                {"id": "circle_1", "type": "circle", "x": 60, "y": 40, "params": {"radius": 48, "segments": 32}},
                {"id": "transform_1", "type": "transform", "x": 300, "y": 40, "params": {"x": 0, "y": 0, "rotation": 0, "scale": 1}},
                {"id": "output_1", "type": "output", "x": 540, "y": 40, "params": {}},
            ],
            "links": [{"from": "circle_1", "to": "transform_1"}, {"from": "transform_1", "to": "output_1"}],
        }

    def test_valid_geometry_graph_is_accepted_in_project(self):
        project = self.project()
        project["node_graphs"] = [self.graph()]
        errors = validate_project(project)
        self.assertEqual([], errors, "; ".join(errors))

    def test_dangling_node_link_is_rejected(self):
        project = self.project()
        graph = self.graph()
        graph["links"].append({"from": "missing_node", "to": "output_1"})
        project["node_graphs"] = [graph]
        self.assertTrue(any("must reference existing nodes" in error for error in validate_project(project)))

    def test_cycles_are_rejected(self):
        project = self.project()
        graph = self.graph()
        graph["links"].append({"from": "output_1", "to": "circle_1"})
        project["node_graphs"] = [graph]
        self.assertTrue(any("acyclic" in error for error in validate_project(project)))

    def test_duplicate_node_ids_are_rejected(self):
        project = self.project()
        graph = self.graph()
        graph["nodes"].append(dict(graph["nodes"][0]))
        project["node_graphs"] = [graph]
        self.assertTrue(any("duplicate" in error for error in validate_project(project)))


if __name__ == "__main__":
    unittest.main()
