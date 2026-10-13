"""Render-time state shared between command generation and rasterization."""
from dataclasses import dataclass, field
from engine.rendering.render_settings import RenderSettings


@dataclass
class RenderContext:
    settings: RenderSettings
    frame: int = 0
    camera: dict = field(default_factory=dict)
    diagnostics: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def warn(self, message):
        self.diagnostics.append({"severity": "warning", "message": str(message)})
