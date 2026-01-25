#!/bin/bash
# Quick start script for Solana Trading Bot
# Usage: ./start_bot.sh [paper|live]

set -e

MODE=${1:-paper}
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=============================================="
echo "Starting Solana Trading Bot"
echo "Mode: $MODE"
echo "=============================================="
echo ""

# Check if MongoDB is running
if ! pgrep -x "mongod" > /dev/null; then
    echo -e "${YELLOW}⚠ MongoDB is not running!${NC}"
    echo "Start MongoDB first with:"
    echo "  mongod --dbpath ~/data/db &"
    echo ""
    read -p "Press Enter to continue anyway or Ctrl+C to exit..."
fi

# Start backend
echo -e "${GREEN}Starting Backend...${NC}"
cd backend
python3 server.py &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"
cd ..

# Wait a bit for backend to start
sleep 2

# Start Node service
echo -e "${GREEN}Starting Node Trading Service...${NC}"
cd node_service
node trading_service.js &
NODE_PID=$!
echo "Node service started (PID: $NODE_PID)"
cd ..

# Wait a bit for node service to start
sleep 2

# Start frontend
echo -e "${GREEN}Starting Frontend...${NC}"
cd frontend
if command -v yarn &> /dev/null; then
    yarn start &
else
    npm start &
fi
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"
cd ..

echo ""
echo "=============================================="
echo -e "${GREEN}All services started!${NC}"
echo "=============================================="
echo ""
echo "Process IDs:"
echo "  Backend:  $BACKEND_PID"
echo "  Node:     $NODE_PID"
echo "  Frontend: $FRONTEND_PID"
echo ""
echo "Access the dashboard at: http://localhost:3000"
echo ""
echo "To stop all services:"
echo "  kill $BACKEND_PID $NODE_PID $FRONTEND_PID"
echo ""
echo "Or use: pkill -f 'python3 server.py' && pkill -f 'node trading_service.js'"
echo ""

# Save PIDs to file for easy cleanup
echo "$BACKEND_PID" > .backend.pid
echo "$NODE_PID" > .node.pid
echo "$FRONTEND_PID" > .frontend.pid

echo "PIDs saved to .backend.pid, .node.pid, .frontend.pid"
echo ""
