#!/bin/bash
# Setup script for Solana Trading Bot on Termux (Arch Linux)

set -e

echo "=============================================="
echo "Solana Trading Bot - Termux Setup Script"
echo "=============================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${GREEN}Step 1: Checking system requirements${NC}"
echo "----------------------------------------------"

# Check if Python is installed
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✓ Python found: $PYTHON_VERSION"
else
    echo -e "${RED}✗ Python 3 not found. Please install: pkg install python${NC}"
    exit 1
fi

# Check if Node.js is installed
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "✓ Node.js found: $NODE_VERSION"
else
    echo -e "${RED}✗ Node.js not found. Please install: pkg install nodejs${NC}"
    exit 1
fi

# Check if npm/yarn is installed
if command -v yarn &> /dev/null; then
    YARN_VERSION=$(yarn --version)
    echo "✓ Yarn found: $YARN_VERSION"
    PKG_MANAGER="yarn"
elif command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "✓ npm found: $NPM_VERSION"
    PKG_MANAGER="npm"
else
    echo -e "${RED}✗ Package manager not found${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Step 2: Installing Python dependencies${NC}"
echo "----------------------------------------------"
cd backend

# Ask user for installation type
echo ""
echo "Choose installation type:"
echo "1) Minimal (recommended for Arch Linux/Termux - ~40 packages)"
echo "2) Full (all packages - may have compatibility issues)"
read -p "Enter choice [1-2] (default: 1): " choice
choice=${choice:-1}

if [ "$choice" = "1" ]; then
    echo "Installing minimal requirements..."
    if pip install -r requirements.minimal.txt; then
        echo "✓ Python dependencies installed (minimal)"
    else
        echo -e "${YELLOW}⚠ Some packages failed. See ARCH_LINUX_COMPATIBILITY.md for help${NC}"
    fi
else
    echo "Installing full requirements..."
    if pip install --prefer-binary -r requirements.txt; then
        echo "✓ Python dependencies installed (full)"
    else
        echo -e "${YELLOW}⚠ Some Python packages may have failed.${NC}"
        echo "Try: pip install -r requirements.minimal.txt"
    fi
fi
cd ..

echo ""
echo -e "${GREEN}Step 3: Installing Node.js service dependencies${NC}"
echo "----------------------------------------------"
cd node_service
if [ "$PKG_MANAGER" = "yarn" ]; then
    yarn install
else
    npm install
fi
echo "✓ Node.js service dependencies installed"
cd ..

echo ""
echo -e "${GREEN}Step 4: Installing frontend dependencies${NC}"
echo "----------------------------------------------"
cd frontend
if [ "$PKG_MANAGER" = "yarn" ]; then
    yarn install
else
    npm install
fi
echo "✓ Frontend dependencies installed"
cd ..

echo ""
echo -e "${GREEN}Step 5: Verifying installations${NC}"
echo "----------------------------------------------"

# Run test script
if python3 test_fixes.py; then
    echo -e "${GREEN}✓ All code verifications passed!${NC}"
else
    echo -e "${YELLOW}⚠ Some tests failed, but installation may still work${NC}"
fi

echo ""
echo "=============================================="
echo -e "${GREEN}Installation Complete!${NC}"
echo "=============================================="
echo ""
echo "To run the bot:"
echo ""
echo "1. Start MongoDB (if not running):"
echo "   mongod --dbpath ~/data/db &"
echo ""
echo "2. Start Backend (Terminal 1):"
echo "   cd backend"
echo "   python3 server.py"
echo ""
echo "3. Start Node Service (Terminal 2):"
echo "   cd node_service"
echo "   node trading_service.js"
echo ""
echo "4. Start Frontend (Terminal 3):"
echo "   cd frontend"
echo "   npm start    # or: yarn start"
echo ""
echo "5. Access the dashboard:"
echo "   http://localhost:3000"
echo ""
echo "=============================================="
echo "Important Files:"
echo "=============================================="
echo "- ARCH_LINUX_COMPATIBILITY.md : Package compatibility guide"
echo "- requirements.minimal.txt    : Optimized packages (40 vs 127)"
echo "- FIXES_APPLIED.md            : Documentation of all fixes"
echo "- test_fixes.py               : Verification test suite"
echo "- backend/.env                : Backend configuration"
echo ""
echo -e "${YELLOW}Note: Make sure MongoDB is running before starting the bot!${NC}"
echo ""
echo "If you encounter package errors, see:"
echo "  ARCH_LINUX_COMPATIBILITY.md"
echo ""
