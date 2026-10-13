
import sys
import subprocess
import argparse

GROUPS = {
    "web": [
        "requests", "httpx", "aiohttp", "beautifulsoup4", "lxml",
        "fastapi", "uvicorn[standard]", "flask", "django",
        "pydantic", "python-dotenv", "jinja2", "websockets",
        "python-multipart", "gunicorn", "starlette", "itsdangerous",
        "email-validator"
    ],
    "data": [
        "numpy", "pandas", "scipy", "matplotlib", "seaborn",
        "scikit-learn", "sympy", "statsmodels", "polars",
        "openpyxl", "xlsxwriter", "pyarrow", "joblib"
    ],
    "images": [
        "pillow", "opencv-python-headless", "imageio",
        "imageio-ffmpeg", "scikit-image", "qrcode", "cairosvg",
        "tifffile", "pydicom"
    ],
    "ai": [
        "openai", "groq", "google-genai", "huggingface-hub",
        "transformers", "tokenizers", "datasets", "accelerate",
        "sentence-transformers", "chromadb", "faiss-cpu",
        "safetensors", "onnx", "onnxruntime"
    ],
    "database": [
        "sqlalchemy", "alembic", "psycopg[binary]", "pymongo",
        "redis", "celery", "aiosqlite", "sqlmodel"
    ],
    "dev": [
        "pytest", "pytest-cov", "ruff", "black", "mypy",
        "ipython", "jupyterlab", "notebook", "rich", "typer",
        "click", "tqdm", "loguru", "psutil", "orjson",
        "pyyaml", "watchdog", "pre-commit", "coverage",
        "virtualenv", "build", "twine"
    ],
    "security": [
        "cryptography", "passlib[bcrypt]", "argon2-cffi",
        "pyjwt", "bcrypt", "python-jose[cryptography]"
    ],
    "automation": [
        "schedule", "apscheduler", "paramiko", "fabric",
        "pexpect", "playwright", "selenium"
    ],
    "game": [
        "pygame", "panda3d", "ursina"
    ],
    "audio": [
        "soundfile", "librosa", "pydub", "SpeechRecognition"
    ]
}

def run(command):
    print("\n$", " ".join(command), flush=True)
    return subprocess.call(command)

def main():
    parser = argparse.ArgumentParser(
        description="Kyro Python Environment Setup"
    )
    parser.add_argument(
        "--group",
        choices=list(GROUPS) + ["all"],
        default="all",
        help="Choose a package group or all"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("KYRO PYTHON ENVIRONMENT INSTALLER")
    print("Python:", sys.version)
    print("Executable:", sys.executable)
    print("=" * 60)

    if run([sys.executable, "-m", "pip", "--version"]) != 0:
        print("pip is unavailable in this environment.")
        return 1

    groups = list(GROUPS) if args.group == "all" else [args.group]
    failed = []

    for group in groups:
        packages = GROUPS[group]
        print(f"\n[{group.upper()}] {len(packages)} packages")
        result = run([
            sys.executable, "-m", "pip", "install", "--upgrade",
            *packages
        ])
        if result != 0:
            failed.append(group)
            print("Some packages failed; continuing with other groups.")

    print("\n" + "=" * 60)
    print("INSTALLATION FINISHED")
    print("Groups selected:", ", ".join(groups))
    print("Groups with errors:", ", ".join(failed) if failed else "None")
    print("\nChecking installed dependencies...")
    run([sys.executable, "-m", "pip", "check"])
    print("\nInstalled packages:")
    run([sys.executable, "-m", "pip", "list"])
    print("=" * 60)

    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
