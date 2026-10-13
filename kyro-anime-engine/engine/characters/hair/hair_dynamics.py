"""Simple damped spring response for hair tips."""


def step_dynamics(position, velocity, target, *, stiffness=0.2, damping=0.8, delta=1.0):
    if stiffness < 0 or not 0 <= damping <= 1 or delta < 0:
        raise ValueError("Invalid hair dynamics parameters")
    force = tuple((goal - current) * stiffness for current, goal in zip(position, target))
    next_velocity = tuple((speed + acceleration * delta) * damping
                          for speed, acceleration in zip(velocity, force))
    next_position = tuple(current + speed * delta for current, speed in zip(position, next_velocity))
    return next_position, next_velocity
