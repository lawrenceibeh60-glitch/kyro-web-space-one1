"""Character identity and metadata profile."""


def create_profile(name, *, age=None, tags=None, description=""):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Character name is required")
    if age is not None and (not isinstance(age, (int, float)) or age < 0):
        raise ValueError("Age must be non-negative")
    return {"name": name.strip(), "age": age, "tags": list(tags or []),
            "description": description}


def update_profile(profile, updates):
    return {**profile, **updates}
