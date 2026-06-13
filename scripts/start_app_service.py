import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PACKAGED_SITE_PACKAGES = ROOT / "python_packages" / "lib" / "site-packages"


def _base_env() -> dict[str, str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    paths = [str(BACKEND)]
    if PACKAGED_SITE_PACKAGES.exists():
        paths.insert(0, str(PACKAGED_SITE_PACKAGES))
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def check() -> None:
    sys.path.insert(0, str(BACKEND))
    if PACKAGED_SITE_PACKAGES.exists():
        sys.path.insert(0, str(PACKAGED_SITE_PACKAGES))
    from app.core.config import settings
    from app.services.production_security_gates import assert_production_security_gates

    gate_result = assert_production_security_gates(settings)
    print("Clinical Donor App Service startup check")
    print(f"startup_mode={settings.startup_mode}")
    print(f"port={settings.port}")
    print(f"serve_frontend={settings.serve_frontend}")
    print(f"frontend_dist_dir={settings.frontend_dist_dir}")
    print("production_security_gate=passed")
    print(f"production_security_gate_warnings={len(gate_result.warnings)}")
    print(f"backend_path={BACKEND}")
    print("status=ok")


def run() -> int:
    env = _base_env()
    os.environ.update(env)
    for path in reversed(env["PYTHONPATH"].split(os.pathsep)):
        if path and path not in sys.path:
            sys.path.insert(0, path)
    import uvicorn

    port = int(env.get("PORT", "8000"))
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
