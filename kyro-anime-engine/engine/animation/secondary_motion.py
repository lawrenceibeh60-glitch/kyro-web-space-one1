"""Stable spring-like secondary motion for follow-through."""


class Spring:
    def __init__(self, value=0.0, *, stiffness=120.0, damping=18.0, mass=1.0):
        if stiffness <= 0 or damping < 0 or mass <= 0:
            raise ValueError("Spring stiffness and mass must be positive; damping non-negative")
        self.value = float(value)
        self.velocity = 0.0
        self.stiffness, self.damping, self.mass = stiffness, damping, mass

    def step(self, target, dt):
        if dt < 0:
            raise ValueError("dt must be non-negative")
        acceleration = (self.stiffness * (target - self.value) - self.damping * self.velocity) / self.mass
        self.velocity += acceleration * dt
        self.value += self.velocity * dt
        return self.value

    def settle(self, target, *, duration, steps=120):
        if steps < 1:
            raise ValueError("steps must be positive")
        dt = duration / steps
        return [self.step(target, dt) for _ in range(steps)]
