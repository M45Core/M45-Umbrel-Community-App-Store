#!/usr/bin/env python3
"""Dependency-free checks for the M45Core Umbrel community store."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_ID = "m45-gopool"
APP = ROOT / APP_ID
FEE_ADDRESS = "3B86bWqfjdQeLEr8nkeeWU6ygksc2K7MoL"
PINNED_IMAGE = re.compile(
    r"^    image: (?:ghcr\.io/m45core/m45-gopool|rodb2008com/gopool):"
    r"[^@\s]+@sha256:[0-9a-f]{64}$",
    re.MULTILINE,
)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    required = (
        ROOT / "umbrel-app-store.yml",
        APP / "umbrel-app.yml",
        APP / "docker-compose.yml",
        APP / "data/config/config.toml.default",
        APP / "VERSION",
    )
    for path in required:
        require(path.is_file(), f"missing {path.relative_to(ROOT)}", errors)
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1

    store = (ROOT / "umbrel-app-store.yml").read_text(encoding="utf-8")
    manifest = (APP / "umbrel-app.yml").read_text(encoding="utf-8")
    compose = (APP / "docker-compose.yml").read_text(encoding="utf-8")
    config = (APP / "data/config/config.toml.default").read_text(encoding="utf-8")
    version_file = (APP / "VERSION").read_text(encoding="utf-8").strip()
    manifest_version_match = re.search(r'^version:\s*["\']?([^"\'\n]+)', manifest, re.MULTILINE)

    require(re.search(r'^id:\s*["\']?m45["\']?\s*$', store, re.MULTILINE) is not None,
            "store id must be m45", errors)
    require(re.search(rf"^id:\s*{APP_ID}\s*$", manifest, re.MULTILINE) is not None,
            f"app id must be {APP_ID}", errors)
    require("manifestVersion: 1" in manifest, "manifestVersion must be 1", errors)
    require(manifest_version_match is not None, "manifest version is missing", errors)
    if manifest_version_match is not None:
        require(version_file == f"v{manifest_version_match.group(1)}",
                "VERSION must match the manifest version", errors)
    require("dependencies:\n  - bitcoin" in manifest, "Bitcoin dependency is missing", errors)
    require("port: 23080" in manifest, "dashboard port must be 23080", errors)
    require("website: https://m45core.com/umbrel" in manifest,
            "manifest website must point to the public Umbrel guide", errors)
    require("support: https://m45core.com/umbrel" in manifest,
            "manifest support link must open the M45 user manual", errors)
    require("Setup guide and user manual: https://m45core.com/umbrel" in manifest,
            "manifest description must show the M45 user manual", errors)
    require("gallery: []" in manifest, "gallery must remain empty until current screenshots exist", errors)
    require("APP_HOST: m45-gopool_server_1" in compose, "app_proxy host is incorrect", errors)
    require("APP_PORT: 8080" in compose, "app_proxy port is incorrect", errors)
    require(PINNED_IMAGE.search(compose) is not None, "server image must be tag-and-digest pinned", errors)
    require(":latest" not in compose, "mutable latest image tag is forbidden", errors)
    require("container_name:" not in compose, "fixed container names are forbidden", errors)
    require("network_mode:" not in compose, "custom network_mode is not expected", errors)
    require('"23456:23456/tcp"' in compose, "plain Stratum port is missing", errors)
    require("24333" not in compose, "self-signed Stratum TLS port must not be published", errors)
    require("-stratum-tls" not in compose, "Stratum TLS runtime override must remain disabled", errors)
    require("${APP_BITCOIN_DATA_DIR}:/bitcoin:ro" in compose,
            "Bitcoin data must be mounted read-only for RPC cookie auth", errors)
    require("- -rpc-cookie=/bitcoin/.cookie" in compose,
            "Bitcoin RPC cookie override is missing", errors)
    require("- -max-conns=512" in compose,
            "home-LAN miner connection cap must be 512", errors)
    require("-allow-rpc-creds" not in compose,
            "deprecated secrets-file RPC authentication must not be enabled", errors)
    require("pool_fee_percent = 2.0" in config, "default pool fee must be 2%", errors)
    require("operator_donation_percent = 0.0" in config,
            "operator donation split must be disabled", errors)
    require(f'payout_address = "{FEE_ADDRESS}"' in config,
            "default fee payout address is incorrect", errors)
    require('pool_entropy = ""' in config,
            "pool entropy must be generated uniquely on first start", errors)
    require('rpc_cookie_path = "/bitcoin/.cookie"' in config,
            "default RPC cookie path is incorrect", errors)
    require('server_location = "Home LAN"' in config,
            "home-LAN location label is missing", errors)
    require('status_connect_miner_title_extra = "Setup help and shareable guide"' in config,
            "dashboard setup-guide label is missing", errors)
    require('status_connect_miner_title_extra_url = "https://m45core.com/umbrel"' in config,
            "dashboard setup-guide URL is missing", errors)
    require('stratum_tls_listen = ""' in config,
            "Stratum TLS must be disabled by default", errors)
    require("__BITCOIN_NODE_IP__" in config, "Bitcoin node template address is missing", errors)

    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print("M45Core Umbrel store validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
