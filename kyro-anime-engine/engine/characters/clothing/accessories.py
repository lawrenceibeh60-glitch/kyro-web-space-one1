"""Attach and validate accessory components."""


def attach_accessory(garment, accessory, anchor):
    if not accessory.get("id") or not isinstance(anchor, (list, tuple)) or len(anchor) < 2:
        raise ValueError("Accessory requires an id and 2D anchor")
    attached = {**accessory, "anchor": tuple(anchor)}
    garment.setdefault("accessories", []).append(attached)
    return attached
