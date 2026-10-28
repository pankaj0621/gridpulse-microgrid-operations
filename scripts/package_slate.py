"""Build and package the Slate static upload after AppSail has an assigned URL."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GridPulse for Catalyst Slate direct upload.")
    parser.add_argument("--api-url", required=True, help="Deployed AppSail API origin, for example https://gridpulse-api.example.com")
    parser.add_argument("--output", type=Path, default=ROOT / "release" / "GridPulse_Slate_Build.zip")
    args = parser.parse_args()
    api_url = args.api_url.strip().rstrip("/")
    parsed = urlparse(api_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        parser.error("--api-url must be an absolute http(s) AppSail origin.")

    environment = os.environ.copy()
    environment["VITE_API_BASE_URL"] = api_url
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise RuntimeError("npm was not found on PATH; install Node.js and npm before packaging Slate.")
    # Windows exposes npm as a .cmd launcher, which subprocess cannot execute
    # directly with shell=False. Keep the shell command fixed; the API URL is
    # passed only through the environment above.
    if os.name == "nt":
        subprocess.run(f'"{npm}" run build', cwd=ROOT, env=environment, check=True, shell=True)
    else:
        subprocess.run([npm, "run", "build"], cwd=ROOT, env=environment, check=True)

    dist = ROOT / "dist"
    if not (dist / "index.html").is_file():
        raise RuntimeError("Vite build completed without dist/index.html.")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=8) as archive:
        for file in sorted(dist.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(dist).as_posix())

    with zipfile.ZipFile(output) as archive:
        corrupted = archive.testzip()
        if corrupted:
            raise RuntimeError(f"Slate archive contains a corrupt file: {corrupted}")
        names = set(archive.namelist())
        if "index.html" not in names or not any(name.startswith("assets/") for name in names):
            raise RuntimeError("Slate archive is missing the built HTML or assets.")
        for name in names:
            if name.startswith("assets/") and name.endswith(".js"):
                bundle = archive.read(name).decode("utf-8", errors="replace")
                if api_url not in bundle:
                    raise RuntimeError("Built frontend bundle does not contain the configured AppSail API origin.")
    print(f"Verified {output} ({output.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
