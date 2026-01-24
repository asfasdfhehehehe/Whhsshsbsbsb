# Solana Trading Bot

A comprehensive Solana trading bot with real-time data collection, automated trading, and risk management.

## Features

### Core Functionality
- **Real-time Data Collection**: Fetches token data from alph.ai API every 100ms
- **Token Filtering**: Only trades tokens with age < 10 seconds
- **Anti-Duplicate**: Ensures each token is purchased only once
- **Batch Trading**: Processes up to 2 tokens per transaction for efficiency
- **DEX Support**: Automatic DEX detection (Meteora, Pump.fun, Raydium, etc.)

### Risk Management
- **Take Profit**: Automatically sells at 12% profit (configurable)
- **Stop Loss**: Exits at 30% loss (configurable)
- **Time-Based Exit**: Closes positions after 6 minutes (configurable)
- **Liquidity Monitoring**: Sells if liquidity drops below 70% of entry level

### Trading Modes
- **Paper Trading**: Test strategies without risking real funds
- **Live Trading**: Execute real trades on Solana mainnet

### User Interface
- Modern tactical terminal design
- Real-time WebSocket updates
- Live position tracking with PnL
- Activity log
- Configurable settings
- Start/Stop controls

## Technology Stack

- **Backend**: Python (FastAPI)
- **Transaction Engine**: Node.js (solana-trade package)
- **Frontend**: React
- **Database**: MongoDB
- **Real-time**: WebSocket
- **DEX Integration**: Jito for MEV protection

## Setup Instructions

### Prerequisites
- Python 3.9+
- Node.js 16+
- MongoDB

### Installation

1. **Backend Setup**
```bash
cd /app/backend
pip install -r requirements.txt
```

2. **Node.js Trading Service**
```bash
cd /app/node_service
yarn install
```

3. **Frontend Setup**
```bash
cd /app/frontend
yarn install
```

### Configuration

The bot is pre-configured with a TEST wallet:
- Public Key: `BQ72nSv9f3PRyRKCBnHLVrerrv37CYTHm5h3s9VSGQDV`
- Private Key: (Hardcoded for testing - stored in Dashboard.js)

**⚠️ WARNING**: Never use this wallet with real funds! Replace with your own wallet for production.

### Environment Variables

Backend (.env):
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=test_database
CORS_ORIGINS=*
```

Frontend (.env):
```
REACT_APP_BACKEND_URL=https://your-domain.com
```

### Running the Bot

All services are managed by Supervisor:

```bash
# Check status
sudo supervisorctl status

# Restart all services
sudo supervisorctl restart all

# View logs
tail -f /var/log/supervisor/backend.err.log
tail -f /var/log/supervisor/node_service.out.log
tail -f /var/log/supervisor/frontend.err.log
```

### Access the Dashboard

Open your browser and navigate to:
- Local: `http://localhost:3000`
- Production: Your configured domain

## Usage

### Starting the Bot

1. Open the dashboard
2. Configure trading parameters in the Settings panel:
   - Amount per Trade (SOL)
   - Take Profit %
   - Stop Loss %
   - Time Exit (minutes)
   - Slippage %

3. Toggle Paper Trading (recommended for testing)
4. Click "START BOT"

### Monitoring

The dashboard displays:
- **Stats**: Total trades, win rate, PnL, active positions
- **Active Positions**: Real-time position tracking with entry price, PnL
- **Activity Log**: All bot actions and events
- **Settings**: Adjustable parameters (locked while bot is running)

### Stopping the Bot

Click "STOP BOT" to safely stop all trading activities. Active positions will remain open.

## Architecture

### Backend (Python)
- `server.py`: Main FastAPI server with WebSocket support
- `data_fetcher.py`: Continuous token data collection from alph.ai
- `trading_engine.py`: Trading logic and risk management
- `position_manager.py`: Position tracking and statistics

### Node.js Service
- `trading_service.js`: Solana transaction execution using solana-trade package
- Handles buy/sell trades via Jito for MEV protection
- Supports batch trading

### Frontend (React)
- `Dashboard.js`: Main trading interface
- Real-time WebSocket connection
- Responsive design with Manrope and JetBrains Mono fonts
- Solana-themed colors (green #14F195, purple #9945FF)

## API Endpoints

### Bot Control
- `POST /api/bot/control` - Start/stop bot
- `GET /api/bot/status` - Get bot status

### Positions
- `GET /api/positions/active` - Get active positions
- `GET /api/positions/closed` - Get closed positions

### Stats
- `GET /api/stats` - Get trading statistics

### WebSocket
- `WS /api/ws` - Real-time updates

## Trading Logic

1. **Token Discovery**: Data fetcher monitors alph.ai API every 100ms
2. **Filtering**: Only tokens < 10 seconds old are selected
3. **Anti-Duplicate**: Tracks seen tokens to prevent double-buying
4. **Batch Execution**: Groups up to 2 tokens per transaction
5. **Position Opening**: Tracks entry price, liquidity, timestamp
6. **Monitoring**: Continuously checks positions against exit conditions
7. **Exit Execution**: Automatically sells when conditions are met

## Risk Warnings

⚠️ **IMPORTANT RISK DISCLAIMERS**:

1. **Financial Risk**: Trading cryptocurrencies involves substantial risk of loss
2. **Beta Software**: This bot is for educational/testing purposes
3. **No Guarantees**: Past performance doesn't indicate future results
4. **MEV Risk**: Despite protection, sandwich attacks are still possible
5. **Smart Contract Risk**: Unaudited tokens may have malicious code
6. **Liquidity Risk**: Low liquidity tokens can suffer severe slippage
7. **Technical Risk**: Network issues, bugs, or downtime can cause losses

**Always test with paper trading first!**

## Default Configuration

```json
{
  "amount_per_trade": 0.1,
  "take_profit_percent": 12,
  "stop_loss_percent": 30,
  "time_exit_minutes": 6,
  "liquidity_drop_percent": 30,
  "slippage": 5
}
```

## Troubleshooting

### WebSocket Connection Failed
- Check that the backend is running: `sudo supervisorctl status backend`
- Verify REACT_APP_BACKEND_URL in frontend/.env

### Node Service Errors
- Check logs: `tail -f /var/log/supervisor/node_service.err.log`
- Restart service: `sudo supervisorctl restart node_service`

### No New Tokens Detected
- Verify alph.ai API is accessible
- Check backend logs for data fetcher errors
- Ensure filter settings (age < 10s) aren't too restrictive

### Trade Execution Failed
- Confirm wallet has sufficient SOL balance
- Check slippage tolerance
- Verify private key is correct
- Review Node service logs

## Development

### Adding New DEX Support
1. Update `DEX_PLATFORMS` mapping in `trading_service.js`
2. Ensure solana-trade package supports the DEX
3. Test with paper trading first

### Modifying Risk Parameters
1. Update config in Dashboard.js
2. Test thoroughly with paper trading
3. Monitor actual behavior before live trading

## Support

For issues or questions:
1. Check logs first
2. Review this README
3. Test in paper trading mode
4. Verify all services are running

## License

This is a TEST/EDUCATIONAL project. Use at your own risk.

---

**Made with Emergent AI** 🚀
