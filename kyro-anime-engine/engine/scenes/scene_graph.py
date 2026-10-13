"""Mutable scene hierarchy with cycle-safe parent operations."""
from engine.scenes.hierarchy import children_of, node_map


class SceneGraph:
    def __init__(self, nodes=()):
        self.nodes = list(nodes)
        self.validate()

    def validate(self):
        by_id = node_map(self.nodes)
        if len(by_id) != len(self.nodes):
            raise ValueError("Scene node ids must be present and unique")
        for node in self.nodes:
            parent = node.get("parent_id")
            if parent is not None and parent not in by_id:
                raise ValueError(f"Parent node not found: {parent}")
        for node in self.nodes:
            self._assert_no_cycle(node["id"], by_id)

    @staticmethod
    def _assert_no_cycle(node_id, by_id):
        seen, current = set(), node_id
        while current is not None:
            if current in seen:
                raise ValueError(f"Cycle detected at scene node {current}")
            seen.add(current)
            current = by_id[current].get("parent_id")

    def add(self, node):
        if any(item.get("id") == node.get("id") for item in self.nodes):
            raise ValueError(f"Duplicate scene node id: {node.get('id')}")
        self.nodes.append(node)
        try:
            self.validate()
        except Exception:
            self.nodes.pop()
            raise
        return node

    def children(self, parent_id):
        return children_of(self.nodes, parent_id)

    def reparent(self, node_id, parent_id):
        by_id = node_map(self.nodes)
        if node_id not in by_id or (parent_id is not None and parent_id not in by_id):
            raise KeyError("Node or parent not found")
        previous = by_id[node_id].get("parent_id")
        by_id[node_id]["parent_id"] = parent_id
        try:
            self.validate()
        except Exception:
            by_id[node_id]["parent_id"] = previous
            raise
