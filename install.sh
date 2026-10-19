#!/usr/bin/env bash
# ccm installer — copies the CLI into ~/.local/bin and wires up fish.
#
# Usage:
#   ./install.sh                  install (idempotent)
#   ./install.sh --with-picker    also add ccm presets to Claude Code's /model picker
#   ./install.sh --refresh        refresh the OpenRouter model catalog too
#
# The actual work is done by `ccm install`; see `ccm install --help`.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "ccm: python3 is required but was not found on PATH" >&2
    exit 1
fi

exec python3 "$REPO_DIR/bin/ccm" install "$@"
