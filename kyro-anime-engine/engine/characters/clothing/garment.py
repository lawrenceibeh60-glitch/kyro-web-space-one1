"""Garment model and piece validation."""
from dataclasses import dataclass, field


@dataclass
class Garment:
    id: str
    kind: str
    color: str = "#808080"
    pieces: list = field(default_factory=list)
    accessories: list = field(default_factory=list)

    def add_piece(self, piece):
        if not piece.get("id") or not piece.get("outline"):
            raise ValueError("Garment piece needs an id and outline")
        self.pieces.append(piece)
        return piece
