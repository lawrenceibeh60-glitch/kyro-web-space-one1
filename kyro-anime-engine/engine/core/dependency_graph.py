"""Directed dependency graph with stable topological ordering."""
from engine.core.errors import DependencyCycleError


class DependencyGraph:
    def __init__(self):
        self._dependencies = {}

    def add(self, node, dependencies=()):
        self._dependencies.setdefault(node, set()).update(dependencies)
        for dependency in dependencies:
            self._dependencies.setdefault(dependency, set())

    def remove(self, node):
        self._dependencies.pop(node, None)
        for dependencies in self._dependencies.values():
            dependencies.discard(node)

    def dependencies(self, node):
        return frozenset(self._dependencies.get(node, ()))

    def topological_order(self):
        remaining = {node: set(deps) for node, deps in self._dependencies.items()}
        ready = [node for node, deps in remaining.items() if not deps]
        result = []
        while ready:
            node = ready.pop(0)
            result.append(node)
            for other, deps in remaining.items():
                if node in deps:
                    deps.remove(node)
                    if not deps and other not in result and other not in ready:
                        ready.append(other)
        if len(result) != len(remaining):
            cyclic = [node for node, deps in remaining.items() if deps]
            raise DependencyCycleError("Dependency cycle detected", cyclic)
        return result

    def __contains__(self, node):
        return node in self._dependencies
