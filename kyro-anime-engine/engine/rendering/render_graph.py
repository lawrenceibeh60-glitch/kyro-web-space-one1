"""Dependency-ordered render pass graph."""
from engine.core.dependency_graph import DependencyGraph


class RenderGraph:
    def __init__(self):
        self._graph = DependencyGraph()
        self._passes = {}

    def add_pass(self, name, callback, *, depends_on=()):
        self._passes[name] = callback
        self._graph.add(name, depends_on)

    def execute(self, context):
        outputs = {}
        for name in self._graph.topological_order():
            outputs[name] = self._passes[name](context, outputs)
        return outputs
