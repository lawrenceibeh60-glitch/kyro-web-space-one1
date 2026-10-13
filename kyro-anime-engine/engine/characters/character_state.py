"""Named character pose/state and component overrides."""
from copy import deepcopy


def capture_state(character, name):
    data = character.to_dict() if hasattr(character, "to_dict") else character
    return {"name": name, "components": deepcopy(data.get("components", {}))}


def apply_state(character, state, *, overwrite=True):
    target = character.components if hasattr(character, "components") else character.setdefault("components", {})
    for key, value in state.get("components", {}).items():
        if overwrite or key not in target:
            target[key] = deepcopy(value)
    return character
