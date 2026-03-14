#!/bin/bash

# OURE (Orbital Uncertainty & Risk Engine) Installer
# Inspired by the Homebrew installation experience.

set -e

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==>${NC} ${BOLD}Starting OURE Installation...${NC}"

# 1. Check for Python 3.11+
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found. Please install Python 3.11 or higher.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$PYTHON_VERSION < 3.11" | bc -l) )); then
    echo -e "${RED}Error: OURE requires Python 3.11+. Found: $PYTHON_VERSION${NC}"
    exit 1
fi

# 2. Define Paths
INSTALL_DIR="$HOME/.oure/app"
BIN_DIR="$HOME/.local/bin"
EXECUTABLE="$BIN_DIR/oure"

echo -e "${BLUE}==>${NC} Preparing installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# 3. Create Virtual Environment
echo -e "${BLUE}==>${NC} Creating self-contained virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"

# 4. Install OURE
echo -e "${BLUE}==>${NC} Installing OURE Risk Engine..."
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip --quiet
# Note: In a real curl-install, this would point to a URL or a GitHub Repo
# For now, it installs from the current directory if available, or PyPI.
if [ -d "./oure" ]; then
    "$INSTALL_DIR/venv/bin/pip" install . --quiet
else
    # Fallback to PyPI if you have uploaded it
    "$INSTALL_DIR/venv/bin/pip" install oure-risk-engine --quiet
fi

# 5. Create Symlink/Wrapper
echo -e "${BLUE}==>${NC} Creating global command link..."
cat <<EOF > "$EXECUTABLE"
#!/bin/bash
export PYTHONPATH="$INSTALL_DIR"
"$INSTALL_DIR/venv/bin/oure" "\$@"
EOF
chmod +x "$EXECUTABLE"

# 6. Check if BIN_DIR is in PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${RED}Warning: $BIN_DIR is not in your PATH.${NC}"
    echo -e "Add this to your .zshrc or .bash_profile:"
    echo -e "  export PATH=\"\$PATH:$BIN_DIR\""
fi

echo -e "${GREEN}==>${NC} ${BOLD}OURE Installation Successful!${NC}"
echo -e "${BLUE}==>${NC} Type 'oure --help' to get started."
