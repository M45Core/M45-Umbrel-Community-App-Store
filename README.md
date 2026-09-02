# M45Core Umbrel Community App Store

This is M45Core's community store for apps distributed outside Umbrel's
official App Store. It currently packages
[M45 goPool](https://github.com/M45Core/M45-goPool), a self-hosted solo Bitcoin
mining pool connected to the Bitcoin Node app on the same Umbrel.

## Add the store to Umbrel

After this repository is published, open the App Store in umbrelOS, choose the
Community App Stores manager, and add:

```text
https://github.com/M45Core/M45-Umbrel-Community-App-Store
```

Install **Bitcoin Node** first and keep it on mainnet. Then install **M45
goPool** from the M45Core store. The Bitcoin dependency supplies RPC and ZMQ
connection details automatically.

## Miner connection

Point miners at the LAN address of the Umbrel host:

```text
stratum+tcp://<umbrel-lan-ip>:23456
```

Use a valid mainnet Bitcoin address as the username. A worker suffix is also
supported, for example:

```text
bc1qexampleaddress.worker-1
```

The password may be any value (commonly `x`). Stratum TLS is available on port
`24333` with a self-signed certificate.

## Fee default

Fresh installs default to a 2% pool fee paid to:

```text
3B86bWqfjdQeLEr8nkeeWU6ygksc2K7MoL
```

The remaining 98% is paid to the valid Bitcoin address supplied by the miner.
The separate operator-donation split is disabled. Existing installs keep their
persisted configuration across app updates.

## Persistent Umbrel test container

The included helper follows Umbrel's current privileged-container test method,
pins umbrelOS `1.7.4` by digest, and uses a named Docker volume. It is intended
to be a long-lived test Umbrel where you can sync a Bitcoin node and connect
physical miners—not an automatically discarded test fixture.

Requirements:

- A Linux Docker host with enough disk for the Bitcoin blockchain
- Ports needed by Umbrel, including host ports 80 and 443, available
- A host reachable from miners on your LAN

Start or resume the same Umbrel installation:

```bash
./scripts/umbrel-container.sh start
```

Complete onboarding at `http://localhost`, install Bitcoin Node, wait for its
initial block download if you intend to mine against a fully synced node, then
add this community store through the Umbrel UI.

Useful commands:

```bash
./scripts/umbrel-container.sh status
./scripts/umbrel-container.sh logs --follow
./scripts/umbrel-container.sh shell
./scripts/umbrel-container.sh stop
./scripts/umbrel-container.sh start
```

`stop`, `start`, `restart`, and `recreate` preserve the named data volume. The
only command that deletes the Umbrel install, Bitcoin chain, and app data is
the deliberately explicit:

```bash
./scripts/umbrel-container.sh destroy --yes
```

The test method is based on Umbrel's
[official app testing guide](https://github.com/getumbrel/umbrel-apps/blob/master/.claude/skills/umbrel-test-app/SKILL.md).
It is known to work on Linux and OrbStack; other Docker Desktop or WSL setups
may need host-specific changes for systemd, privileged containers, or host
networking.

## Release automation

M45-goPool owns the container build; this store owns its package metadata.
For each semantic release tag, the source workflow:

1. creates the GitHub release if necessary;
2. builds `linux/amd64` and `linux/arm64` images;
3. publishes an immutable version tag to `ghcr.io/m45core/m45-gopool`; and
4. dispatches the resulting multi-platform digest to this repository.

This repository verifies the source tag and image digest, updates the app
version/release notes/image pin, validates the package, and commits the update
with its own `GITHUB_TOKEN`. It can also be run manually for an existing tag.

One-time setup:

- Make the `ghcr.io/m45core/m45-gopool` package public so Umbrel can pull it.
- In `M45Core/M45-goPool`, add `UMBREL_STORE_TOKEN`, a fine-grained token with
  Contents read/write access to this repository. It is used only to send the
  `repository_dispatch` event.
- Enable Actions write access in this repository so its update workflow can
  commit package metadata.

The bootstrap package is pinned to RodB's multi-platform v0.3.2 image so it can
be tested before M45Core's GHCR package exists. Running the updated source
release workflow for existing tag `v0.3.4` (or creating the next tag) replaces
that bootstrap image with M45Core's own immutable image automatically.

## Validation

Run the dependency-free policy checks and render the Compose model with test
Umbrel variables:

```bash
python3 scripts/validate-store.py

APP_DATA_DIR=/tmp/m45-gopool \
APP_BITCOIN_NETWORK=mainnet \
APP_BITCOIN_NODE_IP=10.21.21.8 \
APP_BITCOIN_RPC_PORT=8332 \
APP_BITCOIN_RPC_USER=umbrel \
APP_BITCOIN_RPC_PASS=validation-only \
APP_BITCOIN_ZMQ_RAWBLOCK_PORT=28332 \
APP_BITCOIN_ZMQ_HASHBLOCK_PORT=28334 \
docker compose --file m45-gopool/docker-compose.yml config --no-consistency --quiet
```

The same checks run on every push and pull request.

## Security note

Umbrel community apps are not reviewed by Umbrel. Review the package and its
pinned images before installing it, keep the Umbrel host patched, and expose
the miner ports only to networks you trust.
