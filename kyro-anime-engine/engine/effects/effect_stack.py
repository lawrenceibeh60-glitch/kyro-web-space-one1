"""Ordered effect registry and frame-filtered effect execution."""
from engine.effects.effect_timing import active


class EffectStack:
    def __init__(self, effects=()):
        self.effects = [dict(effect) for effect in effects]

    def add(self, effect):
        effect_id = effect.get("id")
        if not effect_id or any(item.get("id") == effect_id for item in self.effects):
            raise ValueError("Effect id must be non-empty and unique")
        self.effects.append(dict(effect))

    def remove(self, effect_id):
        before = len(self.effects)
        self.effects = [effect for effect in self.effects if effect.get("id") != effect_id]
        return len(self.effects) != before

    def at(self, frame, scene_id=None):
        return [effect for effect in self.effects
                if active(effect, frame) and (scene_id is None or effect.get("scene_id") == scene_id)]


def apply_effects(value, effects, processor, frame):
    result = value
    for effect in effects:
        if active(effect, frame):
            result = processor(result, effect, frame)
    return result
