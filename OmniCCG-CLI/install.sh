#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────
# OmniCCG-CLI — Installation Script
# Installs all system and Python dependencies required to run
# OmniCCG-CLI with NiCad and/or Simian clone detectors.
# ─────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Check running on Linux ──────────────────────────────────
if [[ "$(uname -s)" != "Linux" ]]; then
    error "This script is intended for Linux. For macOS/Windows, please install dependencies manually (see README.md)."
fi

# ── Detect package manager ──────────────────────────────────
if command -v apt-get &>/dev/null; then
    PKG_MANAGER="apt"
elif command -v dnf &>/dev/null; then
    PKG_MANAGER="dnf"
elif command -v yum &>/dev/null; then
    PKG_MANAGER="yum"
elif command -v pacman &>/dev/null; then
    PKG_MANAGER="pacman"
else
    error "No supported package manager found (apt, dnf, yum, pacman)."
fi

info "Detected package manager: $PKG_MANAGER"

# ── Install system packages ─────────────────────────────────
info "Installing system dependencies (git, gcc, make, perl, python3, pip, java)..."

case "$PKG_MANAGER" in
    apt)
        sudo apt-get update -y
        sudo apt-get install -y \
            git gcc make perl \
            python3 python3-pip python3-venv \
            default-jre curl
        ;;
    dnf)
        sudo dnf install -y \
            git gcc make perl \
            python3 python3-pip \
            java-17-openjdk-headless curl
        ;;
    yum)
        sudo yum install -y \
            git gcc make perl \
            python3 python3-pip \
            java-17-openjdk-headless curl
        ;;
    pacman)
        sudo pacman -Sy --noconfirm \
            git gcc make perl \
            python python-pip \
            jre-openjdk curl
        ;;
esac

info "System packages installed."

# ── Install TXL (required for NiCad) ────────────────────────
if command -v txl &>/dev/null; then
    info "TXL is already installed: $(txl -V 2>&1 | head -1 || echo 'found')"
else
    info "Installing TXL 10.8b (required for NiCad)..."
    TXL_URL="https://txl.ca/download/25536-txl10.8b.linux64.tar.gz"
    TXL_TMP="/tmp/freetxl.tar.gz"

    curl -L -o "$TXL_TMP" "$TXL_URL"
    sudo mkdir -p /opt/txl
    sudo tar -xzf "$TXL_TMP" -C /opt/txl --strip-components=1
    sudo chmod +x /opt/txl/bin/txl
    sudo ln -sf /opt/txl/bin/txl /usr/local/bin/txl
    rm -f "$TXL_TMP"

    if command -v txl &>/dev/null; then
        info "TXL installed successfully."
    else
        warn "TXL binary installed to /opt/txl/bin/txl but not found on PATH. You may need to add it manually."
    fi
fi

# ── Compile NiCad tools ─────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NICAD_DIR="$SCRIPT_DIR/src/omniccg/tools/NiCad"

if [[ -d "$NICAD_DIR" ]]; then
    info "Compiling NiCad tools..."
    (cd "$NICAD_DIR" && make clean && make) || warn "NiCad compilation failed. Check that gcc and txl are installed."
    info "NiCad tools compiled."
else
    warn "NiCad directory not found at $NICAD_DIR — skipping compilation."
fi

# ── Install Python dependencies ─────────────────────────────
info "Installing Python dependencies..."

# Install Poetry if not present
if ! command -v poetry &>/dev/null; then
    info "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
    info "Poetry installed."
else
    info "Poetry is already installed."
fi

cd "$SCRIPT_DIR"

# Install via Poetry
info "Running 'poetry install'..."
poetry install

# Install package in editable mode
info "Running 'pip install -e .'..."
pip install -e .

# ── Verify installation ─────────────────────────────────────
echo ""
info "────────────────────────────────────────"
info "  Installation Summary"
info "────────────────────────────────────────"

check_cmd() {
    if command -v "$1" &>/dev/null; then
        echo -e "  ${GREEN}✔${NC} $1"
    else
        echo -e "  ${RED}✘${NC} $1 (not found)"
    fi
}

check_cmd git
check_cmd gcc
check_cmd python3
check_cmd pip
check_cmd poetry
check_cmd txl
check_cmd java
check_cmd perl

echo ""
if command -v omniccg &>/dev/null; then
    echo -e "  ${GREEN}✔${NC} omniccg CLI is available"
else
    warn "omniccg CLI not found on PATH. Try running: source ~/.bashrc"
fi

echo ""
info "Installation complete. Run 'omniccg --help' to get started."
