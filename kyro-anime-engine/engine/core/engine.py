"""Convenience facade that wires common standalone engine services."""
from engine.core.capabilities import Capabilities
from engine.core.context import EngineContext
from engine.core.event_bus import EventBus
from engine.core.registry import Registry


class Engine:
    def __init__(self):
        self.events = EventBus()
        self.services = Registry()
        self.capabilities = Capabilities()

    def context(self, project=None, frame=0, fps=None):
        if fps is None:
            fps = (project or {}).get("settings", {}).get("fps", 12.0)
        return EngineContext(project=project, frame=frame, fps=fps, events=self.events, services=self.services)

    def register_service(self, name, service, *, capability=None):
        self.services.register(name, service, replace=True)
        if capability:
            self.capabilities.provide(capability, service)
        return service
