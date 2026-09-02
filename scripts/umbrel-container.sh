#!/usr/bin/env bash
set -Eeuo pipefail

readonly DEFAULT_IMAGE="ghcr.io/getumbrel/umbrelos:1.7.4@sha256:99e2e1c4493a53ddc471909e4d0f54c12a3ec80af644f6f9f8f6f050d032b95a"
readonly CONTAINER_NAME="${UMBREL_CONTAINER_NAME:-m45-umbrel-test}"
readonly DATA_VOLUME="${UMBREL_DATA_VOLUME:-m45-umbrel-test-data}"
readonly UMBREL_IMAGE="${UMBREL_IMAGE:-${DEFAULT_IMAGE}}"

usage() {
  cat <<'EOF'
Usage: scripts/umbrel-container.sh COMMAND [ARGS]

Persistent umbrelOS test environment:
  start                 Create or start Umbrel; never removes existing data
  stop                  Stop Umbrel while preserving all data
  restart               Restart the existing Umbrel container
  recreate              Replace only the container; preserve its data volume
  status                Show container, image, and persistent volume status
  logs [docker args]    Show logs (example: logs --follow)
  shell                 Open a root shell in the Umbrel container
  exec COMMAND [ARGS]   Run a command in the Umbrel container
  url                   Print the local Umbrel URL and miner ports
  destroy --yes         Permanently remove the container and data volume

Overrides: UMBREL_IMAGE, UMBREL_CONTAINER_NAME, UMBREL_DATA_VOLUME
EOF
}

require_docker() {
  command -v docker >/dev/null 2>&1 || {
    echo "Docker is required." >&2
    exit 1
  }
  docker info >/dev/null 2>&1 || {
    echo "The Docker daemon is not available." >&2
    exit 1
  }
}

container_exists() {
  docker container inspect "${CONTAINER_NAME}" >/dev/null 2>&1
}

container_running() {
  [[ "$(docker inspect --format '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || true)" == "true" ]]
}

create_container() {
  docker volume create "${DATA_VOLUME}" >/dev/null
  docker run \
    --name "${CONTAINER_NAME}" \
    --hostname "${CONTAINER_NAME}" \
    --detach \
    --privileged \
    --network host \
    --restart unless-stopped \
    --stop-timeout 120 \
    --volume "${DATA_VOLUME}:/data" \
    "${UMBREL_IMAGE}" \
    /sbin/init >/dev/null
  echo "Umbrel started. Its persistent data volume is ${DATA_VOLUME}."
  echo "Complete onboarding at http://localhost"
}

start_container() {
  if container_exists; then
    if container_running; then
      echo "${CONTAINER_NAME} is already running."
    else
      docker start "${CONTAINER_NAME}" >/dev/null
      echo "${CONTAINER_NAME} started with its existing ${DATA_VOLUME} data."
    fi
  else
    create_container
  fi
}

require_container() {
  container_exists || {
    echo "${CONTAINER_NAME} does not exist; run '$0 start' first." >&2
    exit 1
  }
}

require_running() {
  require_container
  container_running || {
    echo "${CONTAINER_NAME} is stopped; run '$0 start' first." >&2
    exit 1
  }
}

main() {
  local command="${1:-}"
  if [[ -z "${command}" ]]; then
    usage
    exit 1
  fi
  shift

  if [[ "${command}" == "help" || "${command}" == "-h" || "${command}" == "--help" ]]; then
    usage
    exit 0
  fi
  require_docker

  case "${command}" in
    start)
      start_container
      ;;
    stop)
      require_container
      if container_running; then
        docker stop "${CONTAINER_NAME}" >/dev/null
        echo "${CONTAINER_NAME} stopped; ${DATA_VOLUME} was preserved."
      else
        echo "${CONTAINER_NAME} is already stopped; ${DATA_VOLUME} is preserved."
      fi
      ;;
    restart)
      require_container
      docker restart "${CONTAINER_NAME}" >/dev/null
      echo "${CONTAINER_NAME} restarted; ${DATA_VOLUME} was preserved."
      ;;
    recreate)
      if container_exists; then
        if container_running; then
          docker stop --time 120 "${CONTAINER_NAME}" >/dev/null
        fi
        docker rm "${CONTAINER_NAME}" >/dev/null
      fi
      create_container
      echo "The container was recreated; ${DATA_VOLUME} was preserved."
      ;;
    status)
      echo "container: ${CONTAINER_NAME}"
      echo "volume:    ${DATA_VOLUME}"
      echo "requested: ${UMBREL_IMAGE}"
      if container_exists; then
        docker inspect --format 'state:     {{.State.Status}}\ncreated:   {{.Created}}\nimage:     {{.Config.Image}}' "${CONTAINER_NAME}"
      else
        echo "state:     not created"
      fi
      docker volume inspect --format 'volume created: {{.CreatedAt}}' "${DATA_VOLUME}" 2>/dev/null || true
      ;;
    logs)
      require_container
      if (($# == 0)); then
        docker logs --tail 200 "${CONTAINER_NAME}"
      else
        docker logs "$@" "${CONTAINER_NAME}"
      fi
      ;;
    shell)
      require_running
      docker exec --interactive --tty "${CONTAINER_NAME}" /bin/bash 2>/dev/null || \
        docker exec --interactive --tty "${CONTAINER_NAME}" /bin/sh
      ;;
    exec)
      require_running
      (($# > 0)) || {
        echo "exec requires a command." >&2
        exit 1
      }
      docker exec --interactive --tty "${CONTAINER_NAME}" "$@"
      ;;
    url)
      echo "Umbrel:          http://localhost"
      echo "goPool Stratum:  <Docker-host-LAN-IP>:23456"
      ;;
    destroy)
      if [[ "${1:-}" != "--yes" ]]; then
        echo "Refusing to delete persistent Umbrel data without: $0 destroy --yes" >&2
        exit 1
      fi
      if container_exists; then
        if container_running; then
          docker stop --time 120 "${CONTAINER_NAME}" >/dev/null
        fi
        docker rm "${CONTAINER_NAME}" >/dev/null
      fi
      if docker volume inspect "${DATA_VOLUME}" >/dev/null 2>&1; then
        docker volume rm "${DATA_VOLUME}" >/dev/null
      fi
      echo "Removed ${CONTAINER_NAME} and persistent volume ${DATA_VOLUME}."
      ;;
    *)
      echo "Unknown command: ${command}" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
