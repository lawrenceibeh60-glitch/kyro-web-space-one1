"""Visibility checks that account for hidden ancestors."""
from engine.scenes.hierarchy import ancestors, node_map


def is_visible(node, nodes=()):
    if not node.get("visible", True):
        return False
    by_id = node_map(nodes)
    parent_id = node.get("parent_id")
    seen = set()
    while parent_id is not None:
        if parent_id in seen:
            return False
        seen.add(parent_id)
        parent = by_id.get(parent_id)
        if parent is None:
            return False
        if not parent.get("visible", True):
            return False
        parent_id = parent.get("parent_id")
    return True


def visible_descendant_ids(nodes, root_id):
    return [
        node.get("id") for node in nodes
        if node.get("id") != root_id and is_visible(node, nodes)
        and any(parent.get("id") == root_id for parent in ancestors(nodes, node.get("id")))
    ]
