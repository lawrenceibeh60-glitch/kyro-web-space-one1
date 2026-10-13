"""Simple damped cloth point integration."""


def integrate_point(position, velocity, acceleration, *, damping=0.98, delta=1.0):
    if not 0 <= damping <= 1 or delta < 0:
        raise ValueError("Invalid cloth integration parameters")
    next_velocity = tuple((speed + force * delta) * damping
                          for speed, force in zip(velocity, acceleration))
    next_position = tuple(value + speed * delta for value, speed in zip(position, next_velocity))
    return next_position, next_velocity
