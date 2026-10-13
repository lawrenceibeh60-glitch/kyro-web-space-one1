"""Reproducible random seed management."""
import random


class SeedManager:
    def __init__(self, seed=None):
        self.seed = seed
        self.random = random.Random(seed)

    def reseed(self, seed):
        self.seed = seed
        self.random.seed(seed)

    def fork(self, label):
        return SeedManager(f"{self.seed}:{label}")
