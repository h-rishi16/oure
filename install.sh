#!/bin/bash

# OURE (Orbital Uncertainty & Risk Engine) - Pro Installer
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}==> Starting OURE Global Installation...${NC}"

# 1. Environment Setup
INSTALL_DIR="$HOME/.oure/app"
BIN_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

echo -e "${BLUE}==>${NC} Setting up sandbox environment..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip --quiet
"$INSTALL_DIR/venv/bin/pip" install .[web] --quiet

# 2. Credential Setup
if [ ! -f "keys.env" ]; then
    echo -e "${YELLOW}==> Space-Track Credentials Required${NC}"
    read -p "Enter Space-Track Email: " st_user
    read -s -p "Enter Space-Track Password: " st_pass
    echo ""
    echo "SPACETRACK_USER=$st_user" > "$INSTALL_DIR/keys.env"
    echo "SPACETRACK_PASS=$st_pass" >> "$INSTALL_DIR/keys.env"
else
    cp keys.env "$INSTALL_DIR/keys.env"
fi

# 3. Create Global Wrapper
echo -e "${BLUE}==>${NC} Linking global 'oure' command..."
cat <<EOF > "$BIN_DIR/oure"
#!/bin/bash
set -o allexport
source "$INSTALL_DIR/keys.env"
set +o allexport
"$INSTALL_DIR/venv/bin/oure" "\$@"
EOF
chmod +x "$BIN_DIR/oure"

# 4. Success Message
echo -e "\n${GREEN}✓ OURE successfully installed to $BIN_DIR/oure${NC}"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${YELLOW}Important:${NC} Add $BIN_DIR to your PATH to use 'oure' from anywhere."
    echo -e "Run this: ${BLUE}echo 'export PATH=\"\$PATH:$BIN_DIR\"' >> ~/.zshrc && source ~/.zshrc${NC}"
else
    echo -e "${BLUE}==>${NC} You can now run: ${GREEN}oure --help${NC}"
fi
