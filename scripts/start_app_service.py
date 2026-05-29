from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def _base_env() -> dict[str, str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    paths = [str(BACKEND)]
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def check() -> None:
    sys.path.insert(0, str(BACKEND))
    from app.core.config import settings

    print("Clinical Donor App Service startup check")
    print(f"startup_mode={settings.startup_mode}")
    print(f"streamlit_port={settings.streamlit_port}")
    print(f"api_internal_port={settings.api_internal_port}")
    print(f"backend_path={BACKEND}")
    print("status=ok")


def run() -> int:
    env = _base_env()
    port = int(env.get("PORT", "8501"))
    api_port = int(env.get("API_INTERNAL_PORT", "8000"))
    env.setdefault("API_URL", f"http://127.0.0.1:{api_port}")

    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(api_port),
    ]
    frontend_cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(ROOT / "frontend" / "app.py"),
        "--server.address=0.0.0.0",
        "--server.port",
        str(port),
        "--server.headless=true",
    ]

    api = subprocess.Popen(api_cmd, cwd=ROOT, env=env)

    def stop_children(*_: object) -> None:
        if api.poll() is None:
            api.terminate()

    signal.signal(signal.SIGTERM, stop_children)
    signal.signal(signal.SIGINT, stop_children)
    try:
        return subprocess.call(frontend_cmd, cwd=ROOT, env=env)
    finally:
        stop_children()
        try:
            api.wait(timeout=10)
        except subprocess.TimeoutExpired:
            api.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description="Azure App Service startup helper")
    parser.add_argument("--check", action="store_true", help="Validate startup imports without launching servers")
    args = parser.parse_args()
    if args.check:
        check()
        return
    raise SystemExit(run())


if __name__ == "__main__":
    main()
