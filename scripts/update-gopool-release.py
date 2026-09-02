#!/usr/bin/env python3
"""Apply one immutable M45-goPool release to the Umbrel package."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


RELEASE_TAG = re.compile(
    r"^v(?P<major>0|[1-9][0-9]*)\."
    r"(?P<minor>0|[1-9][0-9]*)\."
    r"(?P<patch>0|[1-9][0-9]*)"
    r"(?P<suffix>(?:-[0-9A-Za-z][0-9A-Za-z.-]*)?)$"
)
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
EXPECTED_IMAGE = "ghcr.io/m45core/m45-gopool"
TOP_LEVEL_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*:")


def replace_top_level_field(lines: list[str], key: str, replacement: list[str]) -> list[str]:
    field = re.compile(rf"^{re.escape(key)}:")
    start = next((i for i, line in enumerate(lines) if field.match(line)), None)
    if start is None:
        raise ValueError(f"missing top-level manifest field {key!r}")

    end = start + 1
    while end < len(lines) and not TOP_LEVEL_KEY.match(lines[end]):
        end += 1
    return lines[:start] + replacement + lines[end:]


def current_manifest_version(path: Path) -> str:
    match = re.search(r'^version:\s*["\']?([^"\'\n]+)', path.read_text(), re.MULTILINE)
    if match is None:
        raise ValueError("manifest has no version")
    return match.group(1).strip()


def version_key(value: str) -> tuple[int, int, int, int, str] | None:
    match = RELEASE_TAG.fullmatch(value if value.startswith("v") else f"v{value}")
    if match is None:
        return None
    # A final release sorts after a prerelease with the same numeric version.
    suffix = match.group("suffix")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        1 if not suffix else 0,
        suffix,
    )


def update_manifest(path: Path, tag: str, release_notes: str) -> None:
    old_version = current_manifest_version(path)
    old_key = version_key(old_version)
    new_key = version_key(tag)
    if old_key is not None and new_key is not None and new_key < old_key:
        raise ValueError(f"refusing version downgrade from {old_version} to {tag}")

    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    lines = replace_top_level_field(lines, "version", [f'version: "{tag.removeprefix("v")}"\n'])

    notes = release_notes.strip()
    note_lines = ["releaseNotes: |-\n"]
    if notes:
        note_lines.extend(f"  {line}\n" if line else "  \n" for line in notes.splitlines())
    else:
        note_lines.append(f"  M45 goPool {tag}.\n")
    lines = replace_top_level_field(lines, "releaseNotes", note_lines)
    path.write_text("".join(lines), encoding="utf-8")


def update_compose(path: Path, image_ref: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    service_start = next(
        (i for i, line in enumerate(lines) if re.fullmatch(r"  server:\s*\n?", line)),
        None,
    )
    if service_start is None:
        raise ValueError("missing Compose server service")

    service_end = len(lines)
    for i in range(service_start + 1, len(lines)):
        if re.fullmatch(r"  [A-Za-z0-9_.-]+:\s*\n?", lines[i]):
            service_end = i
            break

    image_lines = [
        i
        for i in range(service_start + 1, service_end)
        if re.match(r"^    image:\s*\S+\s*$", lines[i])
    ]
    if len(image_lines) != 1:
        raise ValueError(f"expected one server image, found {len(image_lines)}")
    lines[image_lines[0]] = f"    image: {image_ref}\n"
    path.write_text("".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-dir", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--release-notes-file", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if RELEASE_TAG.fullmatch(args.tag) is None:
        raise SystemExit(f"invalid release tag: {args.tag}")
    if args.image != EXPECTED_IMAGE:
        raise SystemExit(f"unexpected image: {args.image}; expected {EXPECTED_IMAGE}")
    if DIGEST.fullmatch(args.digest) is None:
        raise SystemExit(f"invalid image digest: {args.digest}")

    app_dir = args.app_dir.resolve()
    manifest = app_dir / "umbrel-app.yml"
    compose = app_dir / "docker-compose.yml"
    template = app_dir / "data" / "config" / "config.toml.default"
    for path in (manifest, compose, template, args.release_notes_file):
        if not path.is_file():
            raise SystemExit(f"required file not found: {path}")

    template_text = template.read_text(encoding="utf-8")
    required_defaults = (
        'pool_fee_percent = 2.0',
        'operator_donation_percent = 0.0',
        'payout_address = "3B86bWqfjdQeLEr8nkeeWU6ygksc2K7MoL"',
    )
    for setting in required_defaults:
        if setting not in template_text:
            raise SystemExit(f"required Umbrel default is missing: {setting}")

    image_ref = f"{args.image}:{args.tag}@{args.digest}"
    update_manifest(
        manifest,
        args.tag,
        args.release_notes_file.read_text(encoding="utf-8"),
    )
    update_compose(compose, image_ref)
    (app_dir / "VERSION").write_text(f"{args.tag}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
