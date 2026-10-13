"""Scene hierarchy lookup and parent/child traversal helpers."""


def node_map(nodes):
    return {node.get("id"): node for node in nodes if isinstance(node, dict) and node.get("id") is not None}


def children_of(nodes, parent_id):
    return [node for node in nodes if node.get("parent_id") == parent_id]


def ancestors(nodes, node_id):
    by_id = node_map(nodes)
    result, visited = [], {node_id}
    node = by_id.get(node_id)
    while node and node.get("parent_id") is not None:
        parent_id = node["parent_id"]
        if parent_id in visited:
            raise ValueError("Cycle detected in scene hierarchy")
        visited.add(parent_id)
        node = by_id.get(parent_id)
        if node is None:
            break
        result.append(node)
    return result


def descendants(nodes, node_id):
    result, pending = [], [node_id]
    while pending:
        parent = pending.pop()
        direct = children_of(nodes, parent)
        result.extend(direct)
        pending.extend(node.get("id") for node in direct)
    return result
