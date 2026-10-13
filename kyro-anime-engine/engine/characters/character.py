"""Serializable character model."""
from dataclasses import dataclass, field


@dataclass
class Character:
    id: str
    name: str = "Character"
    profile: dict = field(default_factory=dict)
    components: dict = field(default_factory=dict)

    def set_component(self, name, value):
        self.components[name] = value
        return value

    def to_dict(self):
        return {"id": self.id, "name": self.name, "profile": self.profile,
                "components": self.components}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or not data.get("id"):
            raise ValueError("Character data requires an id")
        return cls(data["id"], data.get("name", "Character"),
                   dict(data.get("profile", {})), dict(data.get("components", {})))
