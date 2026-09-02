#!/usr/bin/env python3
"""Smoke tests for independent source and Umbrel package versions."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPDATER = ROOT / "scripts" / "update-gopool-release.py"
DIGEST = "sha256:" + ("a" * 64)


def run_update(app_dir: Path, umbrel_version: str) -> subprocess.CompletedProcess[str]:
    notes = app_dir.parent / "notes.md"
    notes.write_text("Independent version smoke test.\n", encoding="utf-8")
    return subprocess.run(
        [
            "python3",
            str(UPDATER),
            "--app-dir",
            str(app_dir),
            "--tag",
            "v0.3.5",
            "--umbrel-version",
            umbrel_version,
            "--image",
            "ghcr.io/m45core/m45-gopool",
            "--digest",
            DIGEST,
            "--release-notes-file",
            str(notes),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="m45-umbrel-updater-test-") as temp:
        app_dir = Path(temp) / "m45-gopool"
        shutil.copytree(ROOT / "m45-gopool", app_dir)

        result = run_update(app_dir, "0.1.0")
        if result.returncode != 0:
            raise SystemExit(result.stderr or result.stdout)

        manifest = (app_dir / "umbrel-app.yml").read_text(encoding="utf-8")
        compose = (app_dir / "docker-compose.yml").read_text(encoding="utf-8")
        version = (app_dir / "VERSION").read_text(encoding="utf-8")
        assert 'version: "0.1.0"' in manifest
        assert "Independent version smoke test." in manifest
        assert f"ghcr.io/m45core/m45-gopool:v0.3.5@{DIGEST}" in compose
        assert version == "v0.1.0\n"

        downgrade = run_update(app_dir, "0.0.9")
        assert downgrade.returncode != 0
        assert "refusing version downgrade" in downgrade.stderr

    print("M45Core Umbrel release updater tests passed")


if __name__ == "__main__":
    main()
