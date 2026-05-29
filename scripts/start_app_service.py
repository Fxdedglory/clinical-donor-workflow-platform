import argparse
import os
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
    print(f"port={settings.port}")
    print(f"serve_frontend={settings.serve_frontend}")
    print(f"frontend_dist_dir={settings.frontend_dist_dir}")
    print(f"backend_path={BACKEND}")
    print("status=ok")


def run() -> int:
    import uvicorn

    env = _base_env()
    os.environ.update(env)
    port = int(env.get("PORT", "8000"))
    sys.path.insert(0, str(BACKEND))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
    return 0


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
