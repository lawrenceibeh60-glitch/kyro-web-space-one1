import unittest

from backend.services.validation_service import _check_compositor_graph


class TestCompositorSocketValidation(unittest.TestCase):
    def check_graph(self, nodes, links):
        errors = []
        _check_compositor_graph({"compositor_graph": {"nodes": nodes, "links": links}}, errors)
        return errors

    def test_valid_two_input_compositor_connections(self):
        nodes = [
            {"id": "layers", "type": "render_layers"},
            {"id": "grade", "type": "color_correct"},
            {"id": "over", "type": "alpha_over"},
            {"id": "output", "type": "output"},
        ]
        links = [
            {"from": "layers", "to": "grade", "from_socket": 0, "to_socket": 0},
            {"from": "grade", "to": "over", "from_socket": 0, "to_socket": 0},
            {"from": "layers", "to": "over", "from_socket": 0, "to_socket": 1},
            {"from": "over", "to": "output", "from_socket": 0, "to_socket": 0},
        ]
        self.assertEqual(self.check_graph(nodes, links), [])

    def test_rejects_unknown_nodes_and_invalid_socket_indices(self):
        nodes = [{"id": "layers", "type": "render_layers"}, {"id": "output", "type": "output"}]
        errors = self.check_graph(nodes, [
            {"from": "layers", "to": "output", "from_socket": 1, "to_socket": 0},
        ])
        self.assertTrue(any("source output socket is out of range" in error for error in errors))

    def test_rejects_duplicate_input_connections_and_cycles(self):
        nodes = [
            {"id": "layers", "type": "render_layers"},
            {"id": "grade", "type": "color_correct"},
            {"id": "levels", "type": "levels"},
        ]
        errors = self.check_graph(nodes, [
            {"from": "layers", "to": "grade"},
            {"from": "levels", "to": "grade"},
            {"from": "grade", "to": "levels"},
        ])
        self.assertTrue(any("input socket may only have one connection" in error for error in errors))
        self.assertTrue(any("must be acyclic" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
