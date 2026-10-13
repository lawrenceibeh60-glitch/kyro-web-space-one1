"""Fluent builder for character data."""
from engine.characters.character import Character


class CharacterBuilder:
    def __init__(self, character_id, name="Character"):
        self.character = Character(character_id, name)

    def profile(self, **values):
        self.character.profile.update(values)
        return self

    def component(self, name, value):
        self.character.set_component(name, value)
        return self

    def build(self):
        return self.character
