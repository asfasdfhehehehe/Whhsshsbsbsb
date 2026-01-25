#!/bin/bash
# Stop all Solana Trading Bot services

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Stopping Solana Trading Bot services..."

# Kill using saved PIDs if available
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    kill $BACKEND_PID 2>/dev/null && echo "✓ Backend stopped (PID: $BACKEND_PID)"
    rm .backend.pid
fi

if [ -f .node.pid ]; then
    NODE_PID=$(cat .node.pid)
    kill $NODE_PID 2>/dev/null && echo "✓ Node service stopped (PID: $NODE_PID)"
    rm .node.pid
fi

if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    kill $FRONTEND_PID 2>/dev/null && echo "✓ Frontend stopped (PID: $FRONTEND_PID)"
    rm .frontend.pid
fi

# Fallback: kill by process name
pkill -f "python3 server.py" 2>/dev/null && echo "✓ Backend processes stopped"
pkill -f "node trading_service.js" 2>/dev/null && echo "✓ Node service processes stopped"
pkill -f "react-scripts start" 2>/dev/null && echo "✓ Frontend processes stopped"

echo ""
echo "All services stopped!"
