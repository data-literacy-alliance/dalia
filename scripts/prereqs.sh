#!/usr/bin/env bash
# prereqs.sh — shared prerequisite helpers; source this file, do NOT execute directly.
# Usage: source "$(dirname "${BASH_SOURCE[0]}")/prereqs.sh"

# ── Package manager helpers ───────────────────────────────────────────────────

_pkg_install() {
  local pkg="$1"
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get install -y "$pkg"
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y "$pkg"
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y "$pkg"
  else
    echo "[ERROR] Cannot detect package manager. Install $pkg manually." >&2
    return 1
  fi
}

# ── ensure_openssl ────────────────────────────────────────────────────────────

ensure_openssl() {
  command -v openssl >/dev/null 2>&1 && return 0
  echo "[WARN] openssl is not installed (required for secret generation)."
  printf "Install it now? [Y/n]: "
  local answer
  read -r answer </dev/tty
  case "$answer" in
    n|N)
      echo "[ERROR] openssl is required. Aborting." >&2
      exit 1
      ;;
  esac
  echo "[INFO] Installing openssl..."
  _pkg_install openssl
  command -v openssl >/dev/null 2>&1 || { echo "[ERROR] openssl installation failed." >&2; exit 1; }
  echo "[OK] openssl installed."
}

# ── ensure_node ───────────────────────────────────────────────────────────────

_nvm_load() {
  export NVM_DIR="${HOME}/.nvm"
  # nvm internals use unbound variables — must disable -u around all nvm calls
  set +u
  # shellcheck disable=SC1091
  [ -s "${NVM_DIR}/nvm.sh" ] && . "${NVM_DIR}/nvm.sh"
  set -u
}

_nvm_install_lts() {
  _nvm_load
  set +u
  if ! command -v nvm >/dev/null 2>&1; then
    set -u
    echo "[ERROR] nvm not available after install." >&2
    exit 1
  fi
  nvm install --lts
  nvm use --lts
  set -u
}

ensure_node() {
  if command -v node >/dev/null 2>&1; then
    local ver
    ver=$(node --version | sed 's/v//' | cut -d. -f1)
    if [ "$ver" -ge 18 ]; then
      return 0
    fi
    echo "[WARN] Node.js >=18 required (found v${ver}) — upgrading via nvm..."
    _nvm_load
    if command -v nvm >/dev/null 2>&1; then
      _nvm_install_lts
    else
      echo "[ERROR] nvm not available. Upgrade Node.js manually to >=18." >&2
      exit 1
    fi
    return 0
  fi

  echo "[WARN] node not found (Node.js >=18 required)."
  printf "Install Node.js now via nvm? [Y/n]: "
  local answer
  read -r answer </dev/tty
  case "$answer" in
    n|N)
      echo "[ERROR] Node.js is required. Aborting." >&2
      exit 1
      ;;
  esac

  if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    echo "[ERROR] curl or wget required to install nvm." >&2
    exit 1
  fi

  echo "[INFO] Installing nvm..."
  set +u
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
  else
    wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
  fi
  set -u

  _nvm_install_lts
  command -v node >/dev/null 2>&1 || { echo "[ERROR] Node.js installation failed." >&2; exit 1; }
  echo "[OK] Node.js $(node --version) installed."
}

# ── ensure_pnpm ───────────────────────────────────────────────────────────────

ensure_pnpm() {
  command -v pnpm >/dev/null 2>&1 && return 0
  echo "[INFO] pnpm not found — installing via npm..."
  npm install -g pnpm
  command -v pnpm >/dev/null 2>&1 || { echo "[ERROR] pnpm installation failed." >&2; exit 1; }
}

# ── ensure_podman ─────────────────────────────────────────────────────────────

ensure_podman() {
  command -v podman >/dev/null 2>&1 && return 0
  echo "[ERROR] podman is not available. Install Podman first." >&2
  exit 1
}
