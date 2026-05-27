#!/usr/bin/env bash
# Install the llmprobe binary without a Go toolchain.
#
# Downloads the prebuilt release for your OS/arch from GitHub Releases, verifies
# its SHA-256 checksum, and installs it to ~/.local/bin. Use --source to build
# from source with `go install` instead.
#
# Usage:
#   ./scripts/install-deps.sh            # download a prebuilt binary
#   ./scripts/install-deps.sh --source   # build from source (needs Go)
#   INSTALL_DIR=/usr/local/bin ./scripts/install-deps.sh
set -euo pipefail

REPO="Jwrede/llmprobe"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
BASE="https://github.com/${REPO}/releases/latest/download"

err() { echo "install-deps: $*" >&2; }

if [ "${1:-}" = "--source" ]; then
  if ! command -v go >/dev/null 2>&1; then
    err "go not found; install Go, or run without --source for a prebuilt binary"
    exit 1
  fi
  echo "Building llmprobe from source with go install ..."
  go install "github.com/${REPO}@latest"
  echo "Installed to $(go env GOPATH)/bin/llmprobe"
  exit 0
fi

case "$(uname -s)" in
  Linux) os="linux" ;;
  Darwin) os="darwin" ;;
  *)
    err "unsupported OS $(uname -s). On Windows, download the .zip from"
    err "https://github.com/${REPO}/releases, or run with --source."
    exit 1
    ;;
esac

case "$(uname -m)" in
  x86_64|amd64) arch="amd64" ;;
  arm64|aarch64) arch="arm64" ;;
  *) err "unsupported architecture $(uname -m)"; exit 1 ;;
esac

asset="llmprobe_${os}_${arch}.tar.gz"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "Downloading ${asset} ..."
curl -fsSL "${BASE}/${asset}" -o "${tmp}/${asset}"
curl -fsSL "${BASE}/checksums.txt" -o "${tmp}/checksums.txt"

echo "Verifying checksum ..."
expected="$(awk -v f="${asset}" '$2 == f {print $1}' "${tmp}/checksums.txt")"
if [ -z "${expected}" ]; then
  err "no checksum entry for ${asset} in checksums.txt"
  exit 1
fi
if command -v sha256sum >/dev/null 2>&1; then
  actual="$(sha256sum "${tmp}/${asset}" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  actual="$(shasum -a 256 "${tmp}/${asset}" | awk '{print $1}')"
else
  err "no sha256 tool found (need sha256sum or shasum)"
  exit 1
fi
if [ "${expected}" != "${actual}" ]; then
  err "checksum mismatch for ${asset}"
  err "  expected ${expected}"
  err "  actual   ${actual}"
  exit 1
fi

echo "Extracting ..."
tar -xzf "${tmp}/${asset}" -C "${tmp}"
mkdir -p "${INSTALL_DIR}"
install -m 0755 "${tmp}/llmprobe" "${INSTALL_DIR}/llmprobe"
echo "Installed llmprobe to ${INSTALL_DIR}/llmprobe"

case ":${PATH}:" in
  *":${INSTALL_DIR}:"*) ;;
  *)
    err "warning: ${INSTALL_DIR} is not on your PATH."
    err "Add it with: export PATH=\"${INSTALL_DIR}:\$PATH\""
    ;;
esac

"${INSTALL_DIR}/llmprobe" version 2>/dev/null || true
