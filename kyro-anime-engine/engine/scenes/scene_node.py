"""Generic scene graph node with local transform and visibility state."""
from dataclasses import dataclass, field
from engine.core.identifiers import new_id


@dataclass
class SceneNode:
    name: str = "Node"
    id: str = field(default_factory=lambda: new_id("node"))
    parent_id: str | None = None
    visible: bool = True
    depth: float = 1.0
    transform: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "parent_id": self.parent_id,
            "visible": self.visible, "depth": self.depth,
            "transform": dict(self.transform), "children": list(self.children),
        }
