from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel
import asyncio
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional

from data_fetcher import DataFetcher
from position_manager import PositionManager
from trading_engine import TradingEngine

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
data_fetcher = DataFetcher()
position_manager = PositionManager()
trading_engine = None
active_websockets: List[WebSocket] = []
current_tokens_cache = []

# Pydantic models
class BotConfig(BaseModel):
    private_key: str
    amount_per_trade: float = 0.1
    take_profit_percent: float = 12.0
    stop_loss_percent: float = 30.0
    time_exit_minutes: int = 6
    liquidity_drop_percent: float = 30.0
    slippage: float = 5.0
    paper_trading: bool = True

class BotControl(BaseModel):
    action: str  # 'start' or 'stop'
    config: Optional[BotConfig] = None

@api_router.get("/")
async def root():
    return {"message": "Solana Trading Bot API"}

@api_router.post("/bot/control")
async def control_bot(control: BotControl):
    global trading_engine
    
    if control.action == 'start':
        if not control.config:
            return {"error": "Configuration required to start bot"}
        
        # Initialize trading engine if not exists
        if not trading_engine:
            trading_engine = TradingEngine(position_manager, control.config.dict())
        else:
            trading_engine.update_config(control.config.dict())
        
        trading_engine.start()
        return {"status": "started", "paper_trading": control.config.paper_trading}
    
    elif control.action == 'stop':
        if trading_engine:
            trading_engine.stop()
        return {"status": "stopped"}
    
    return {"error": "Invalid action"}

@api_router.get("/bot/status")
async def get_bot_status():
    if trading_engine:
        return {
            "running": trading_engine.running,
            "paper_trading": trading_engine.paper_trading,
            "config": {
                "amount_per_trade": trading_engine.amount_per_trade,
                "take_profit_percent": trading_engine.take_profit_percent,
                "stop_loss_percent": trading_engine.stop_loss_percent,
                "time_exit_minutes": trading_engine.time_exit_minutes,
                "liquidity_drop_percent": trading_engine.liquidity_drop_percent,
                "slippage": trading_engine.slippage
            }
        }
    return {"running": False, "paper_trading": True}

@api_router.get("/positions/active")
async def get_active_positions():
    positions = position_manager.get_all_active()
    return {"positions": [p.to_dict() for p in positions]}

@api_router.get("/positions/closed")
async def get_closed_positions(limit: int = 20):
    positions = position_manager.get_recent_closed(limit)
    return {"positions": [p.to_dict() for p in positions]}

@api_router.get("/stats")
async def get_stats():
    return position_manager.get_stats()

@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    logger.info('WebSocket client connected')
    
    try:
        while True:
            # Keep connection alive and listen for client messages
            message = await websocket.receive_text()
            
            # Handle ping messages
            if message:
                try:
                    data = json.loads(message)
                    if data.get('type') == 'ping':
                        await websocket.send_text(json.dumps({'type': 'pong'}))
                except:
                    pass
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
        logger.info('WebSocket client disconnected')
    except Exception as e:
        logger.error(f'WebSocket error: {e}')
        if websocket in active_websockets:
            active_websockets.remove(websocket)

async def broadcast_to_websockets(data: dict):
    """Broadcast data to all connected WebSocket clients"""
    if not active_websockets:
        return
    
    message = json.dumps(data)
    disconnected = []
    
    for websocket in active_websockets:
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f'Error sending to websocket: {e}')
            disconnected.append(websocket)
    
    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)

async def token_callback(new_tokens: List[Dict]):
    """Callback for new tokens from data fetcher"""
    global current_tokens_cache
    
    # Broadcast new tokens
    await broadcast_to_websockets({
        'type': 'new_tokens',
        'data': new_tokens,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
    
    # Process tokens with trading engine
    if trading_engine and trading_engine.running:
        await trading_engine.process_new_tokens(new_tokens, broadcast_to_websockets)

async def position_monitor_loop():
    """Background task to monitor positions and calculate real-time PnL"""
    global current_tokens_cache
    
    while True:
        try:
            # Fetch current token data for position monitoring
            tokens = await data_fetcher.fetch_tokens()
            current_tokens_cache = tokens
            
            # Create price lookup
            price_lookup = {token['token']: float(token.get('price', 0)) for token in tokens}
            
            # Update PnL for active positions
            active_positions_with_pnl = []
            for position in position_manager.get_all_active():
                current_price = price_lookup.get(position.mint, 0)
                
                if current_price > 0:
                    # Calculate real-time PnL
                    pnl_sol, pnl_percent = position.calculate_pnl(current_price)
                    pos_dict = position.to_dict()
                    pos_dict['current_price'] = current_price
                    pos_dict['pnl_sol'] = pnl_sol
                    pos_dict['pnl_percent'] = pnl_percent
                else:
                    pos_dict = position.to_dict()
                    pos_dict['current_price'] = position.entry_price
                
                active_positions_with_pnl.append(pos_dict)
            
            # Monitor positions for exit conditions (only if bot is running)
            if trading_engine and trading_engine.running:
                await trading_engine.monitor_positions(tokens, broadcast_to_websockets)
            
            # Broadcast positions and stats
            stats = position_manager.get_stats()
            
            await broadcast_to_websockets({
                'type': 'update',
                'data': {
                    'positions': active_positions_with_pnl,
                    'stats': stats
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            await asyncio.sleep(1)  # Update every second
        except Exception as e:
            logger.error(f'Error in position monitor loop: {e}')
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    logger.info('Starting Solana Trading Bot')
    await data_fetcher.start()
    
    # Start background tasks
    asyncio.create_task(data_fetcher.continuous_fetch(token_callback, interval_ms=100))
    asyncio.create_task(position_monitor_loop())

@app.on_event("shutdown")
async def shutdown_event():
    await data_fetcher.stop()
    client.close()

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
