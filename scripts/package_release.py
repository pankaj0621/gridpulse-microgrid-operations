"""Create and validate clean source and Catalyst deployment ZIP archives."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_FILES = (
    "index.html",
    "package.json",
    "package-lock.json",
    "vite.config.ts",
    "tsconfig.json",
    "tsconfig.app.json",
    "tsconfig.node.json",
    "README.md",
    "DESIGN.md",
    "deployment/README.md",
)
EXCLUDED_PARTS = {
    ".git",
    ".superpowers",
    ".venv",
    "node_modules",
    "dist",
    "release",
    "__pycache__",
    ".data",
    ".pytest_cache",
    ".vitest",
    "coverage",
}


def should_exclude(relative: Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return True
    if relative.suffix in {".pyc", ".pyo", ".sqlite3", ".sqlite3-shm", ".sqlite3-wal"}:
        return True
    name = relative.name
    if name in {".env", ".env.local"}:
        return True
    if name.startswith(".env.") and not name.endswith(".example"):
        return True
    return False


def add_path(archive: zipfile.ZipFile, source: Path, target: str | None = None) -> None:
    if source.is_dir():
        for child in sorted(source.rglob("*")):
            if child.is_file():
                relative = child.relative_to(ROOT)
                if not should_exclude(relative):
                    archive.write(child, (Path(target) / child.relative_to(source)).as_posix() if target else relative.as_posix())
    elif source.is_file():
        relative = source.relative_to(ROOT)
        if not should_exclude(relative):
            archive.write(source, target or relative.as_posix())


def add_frontend(archive: zipfile.ZipFile) -> None:
    for name in FRONTEND_FILES:
        add_path(archive, ROOT / name)
    add_path(archive, ROOT / "src")


def make_source_archive(destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=8) as archive:
        for child in sorted(ROOT.iterdir()):
            if child.name == "scripts":
                add_path(archive, child)
            elif child.name in {
                ".env.example",
                ".gitignore",
                "DESIGN.md",
                "README.md",
                "index.html",
                "package.json",
                "package-lock.json",
                "predict.py",
                "PROBLEM_STATEMENT.md",
                "requirements.txt",
                "sample_test_input.csv",
                "test_eval.py",
                "train_telemetry.csv",
                "tsconfig.app.json",
                "tsconfig.json",
                "tsconfig.node.json",
                "vite.config.ts",
            }:
                add_path(archive, child)
            elif child.name in {"src", "backend", "deployment"}:
                add_path(archive, child)


def make_slate_source_archive(destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=8) as archive:
        add_frontend(archive)


def make_appsail_archive(destination: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="gridpulse-appsail-") as temporary:
        dependency_root = Path(temporary) / "dependencies"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--only-binary=:all:",
                "--platform=manylinux2014_x86_64",
                "--python-version=3.13",
                "--implementation=cp",
                "--abi=cp313",
                "--target",
                str(dependency_root),
                "-r",
                str(ROOT / "backend" / "requirements.txt"),
            ],
            cwd=ROOT,
            check=True,
        )
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=8) as archive:
            archive.write(ROOT / "backend" / "main.py", "main.py")
            archive.write(ROOT / "backend" / "requirements.txt", "requirements.txt")
            for child in sorted((ROOT / "backend" / "app").rglob("*.py")):
                if "__pycache__" not in child.parts:
                    archive.write(child, child.relative_to(ROOT / "backend").as_posix())
            for child in sorted(dependency_root.rglob("*")):
                if child.is_file() and "__pycache__" not in child.parts:
                    archive.write(child, child.relative_to(dependency_root).as_posix())
            archive.writestr("DEPLOY.txt", appsail_deploy_note())
            archive.write(ROOT / "deployment" / "README.md", "README_DEPLOY.md")


def appsail_deploy_note() -> str:
    return """GridPulse AppSail deployment package

Runtime: Catalyst-managed Python 3.13
Startup command: sh -c 'python3 -m uvicorn main:app --host 0.0.0.0 --port ${X_ZOHO_CATALYST_LISTEN_PORT:-9000}'
Python dependencies are bundled for Linux AMD64 / CPython 3.13.
Configure the environment variables and pre-create the Stratus bucket and Data Store tables described in README_DEPLOY.md before enabling Catalyst storage.
Keep QuickML OAuth credentials in AppSail environment variables. Do not add a .env file to this archive.
"""


def verify_archive(path: Path, required: set[str]) -> None:
    with zipfile.ZipFile(path) as archive:
        corrupted = archive.testzip()
        if corrupted:
            raise RuntimeError(f"{path.name} contains a corrupt member: {corrupted}")
        names = set(archive.namelist())
        missing = required - names
        if missing:
            raise RuntimeError(f"{path.name} is missing required files: {', '.join(sorted(missing))}")
        forbidden = [
            name
            for name in names
            if any(part in EXCLUDED_PARTS for part in Path(name).parts)
            or name in {".env", ".env.local"}
            or (Path(name).name.startswith(".env.") and not Path(name).name.endswith(".example"))
        ]
        if forbidden:
            raise RuntimeError(f"{path.name} contains development-only files: {', '.join(sorted(forbidden))}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Package GridPulse source and Catalyst deployment builds.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "release")
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_zip = output_dir / "GridPulse_Source.zip"
    slate_zip = output_dir / "GridPulse_Slate_Source.zip"
    appsail_zip = output_dir / "GridPulse_AppSail.zip"
    make_source_archive(source_zip)
    make_slate_source_archive(slate_zip)
    make_appsail_archive(appsail_zip)

    verify_archive(source_zip, {"README.md", "train_telemetry.csv", "sample_test_input.csv", "predict.py", "deployment/README.md"})
    verify_archive(slate_zip, {"index.html", "package.json", "src/main.tsx"})
    verify_archive(appsail_zip, {"main.py", "requirements.txt", "app/quickml_client.py", "app/catalyst_storage.py", "README_DEPLOY.md", "zcatalyst_sdk/__init__.py", "fastapi/__init__.py"})
    with zipfile.ZipFile(appsail_zip) as archive:
        members = archive.namelist()
        if not any(name.startswith("pydantic_core/_pydantic_core") and name.endswith(".so") for name in members):
            raise RuntimeError("AppSail package is missing the Linux CPython 3.13 Pydantic extension.")
        if any(name.endswith(".pyd") for name in members):
            raise RuntimeError("AppSail package contains a Windows-only Python extension.")
    for path in (source_zip, slate_zip, appsail_zip):
        print(f"Verified {path} ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
