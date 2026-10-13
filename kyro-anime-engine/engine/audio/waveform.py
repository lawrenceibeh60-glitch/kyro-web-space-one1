"""Waveform envelope extraction and display downsampling."""
import math


def peak_envelope(samples, buckets):
    if buckets < 1:
        raise ValueError("buckets must be positive")
    if not samples:
        return [0.0] * buckets
    result = []
    for index in range(buckets):
        start, end = index * len(samples) // buckets, (index + 1) * len(samples) // buckets
        result.append(max((abs(float(value)) for value in samples[start:end]), default=0.0))
    return result


def rms_envelope(samples, buckets):
    if buckets < 1:
        raise ValueError("buckets must be positive")
    result = []
    for index in range(buckets):
        chunk = samples[index * len(samples) // buckets:(index + 1) * len(samples) // buckets]
        result.append(math.sqrt(sum(float(value) ** 2 for value in chunk) / len(chunk)) if chunk else 0.0)
    return result
