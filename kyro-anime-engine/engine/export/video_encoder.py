"""Video encoding through the system ffmpeg executable."""
import shutil
import subprocess


def encode_frames(input_pattern, output_path, *, fps=24, codec="libx264", transparent=False):
    if fps <= 0:
        raise ValueError("fps must be positive")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for video export")
    command = [ffmpeg, "-y", "-framerate", str(fps), "-i", str(input_pattern),
               "-c:v", codec]
    if transparent:
        command.extend(["-pix_fmt", "yuva420p"])
    command.append(str(output_path))
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()}")
    return str(output_path)
