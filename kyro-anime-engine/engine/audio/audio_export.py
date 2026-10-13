"""Audio export from a project audio mixdown."""
import wave


def export_wav(path, samples, *, sample_rate=44100, channels=1):
    if sample_rate <= 0 or channels <= 0 or len(samples) % channels:
        raise ValueError("Invalid sample rate, channel count, or interleaved sample length")
    import struct
    pcm = bytearray()
    for sample in samples:
        pcm.extend(struct.pack("<h", max(-32768, min(32767, round(float(sample) * 32767)))))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm)
    return str(path)
