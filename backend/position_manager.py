from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging
import json
import os
from pathlib import Path
from threading import RLock

logger = logging.getLogger(__name__)

class Position:
    def __init__(self, token: str, mint: str, entry_price: float, amount_sol: float, 
                 token_amount: float, platform: str, liquidity_usdt: float):
        self.token = token
        self.mint = mint
        self.entry_price = entry_price
        self.entry_liquidity = liquidity_usdt
        self.amount_sol = amount_sol
        self.token_amount = token_amount
        self.platform = platform
        self.entry_time = datetime.now(timezone.utc)
        self.exit_price: Optional[float] = None
        self.exit_time: Optional[datetime] = None
        self.pnl_sol: float = 0.0
        self.pnl_percent: float = 0.0
        self.status = 'active'  # active, closed
        self.exit_reason: Optional[str] = None

    def calculate_pnl(self, current_price: float) -> tuple[float, float]:
        """Calculate current PnL"""
        current_value = self.token_amount * current_price
        pnl_sol = current_value - self.amount_sol
        pnl_percent = ((current_value / self.amount_sol) - 1) * 100
        return pnl_sol, pnl_percent

    def close(self, exit_price: float, reason: str):
        """Close position"""
        self.exit_price = exit_price
        self.exit_time = datetime.now(timezone.utc)
        self.pnl_sol, self.pnl_percent = self.calculate_pnl(exit_price)
        self.status = 'closed'
        self.exit_reason = reason

    def to_dict(self) -> dict:
        return {
            'token': self.token,
            'mint': self.mint,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'amount_sol': self.amount_sol,
            'token_amount': self.token_amount,
            'platform': self.platform,
            'entry_time': self.entry_time.isoformat(),
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'pnl_sol': self.pnl_sol,
            'pnl_percent': self.pnl_percent,
            'status': self.status,
            'exit_reason': self.exit_reason,
            'entry_liquidity': self.entry_liquidity
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Position':
        """Create Position from dictionary"""
        position = cls(
            token=data['token'],
            mint=data['mint'],
            entry_price=data['entry_price'],
            amount_sol=data['amount_sol'],
            token_amount=data['token_amount'],
            platform=data['platform'],
            liquidity_usdt=data.get('entry_liquidity', 0)
        )
        
        # Restore timestamps
        position.entry_time = datetime.fromisoformat(data['entry_time'].replace('Z', '+00:00'))
        if data.get('exit_time'):
            position.exit_time = datetime.fromisoformat(data['exit_time'].replace('Z', '+00:00'))
        
        # Restore other fields
        position.exit_price = data.get('exit_price')
        position.pnl_sol = data.get('pnl_sol', 0.0)
        position.pnl_percent = data.get('pnl_percent', 0.0)
        position.status = data.get('status', 'active')
        position.exit_reason = data.get('exit_reason')
        
        return position

class PositionManager:
    def __init__(self, data_dir: str = None):
        self.active_positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # File persistence
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.active_positions_file = self.data_dir / 'active_positions.json'
        self.closed_positions_file = self.data_dir / 'closed_positions.json'
        self.stats_file = self.data_dir / 'stats.json'
        
        # Thread-safe lock for file operations
        self.file_lock = RLock()
        
        # Load existing data on initialization
        self.load_from_files()

    def load_from_files(self):
        """Load positions and stats from files"""
        with self.file_lock:
            try:
                # Load active positions
                if self.active_positions_file.exists():
                    with open(self.active_positions_file, 'r') as f:
                        data = json.load(f)
                        self.active_positions = {
                            mint: Position.from_dict(pos_data)
                            for mint, pos_data in data.items()
                        }
                    logger.info(f'Loaded {len(self.active_positions)} active positions from file')
                
                # Load closed positions
                if self.closed_positions_file.exists():
                    with open(self.closed_positions_file, 'r') as f:
                        data = json.load(f)
                        self.closed_positions = [
                            Position.from_dict(pos_data) for pos_data in data
                        ]
                    logger.info(f'Loaded {len(self.closed_positions)} closed positions from file')
                
                # Load stats
                if self.stats_file.exists():
                    with open(self.stats_file, 'r') as f:
                        stats = json.load(f)
                        self.total_trades = stats.get('total_trades', 0)
                        self.winning_trades = stats.get('winning_trades', 0)
                        self.losing_trades = stats.get('losing_trades', 0)
                    logger.info(f'Loaded stats from file: {self.total_trades} trades')
                
            except Exception as e:
                logger.error(f'Error loading data from files: {e}')

    def save_to_files(self):
        """Save positions and stats to files"""
        with self.file_lock:
            try:
                # Save active positions
                active_data = {
                    mint: position.to_dict()
                    for mint, position in self.active_positions.items()
                }
                with open(self.active_positions_file, 'w') as f:
                    json.dump(active_data, f, indent=2)
                
                # Save closed positions (keep last 1000)
                closed_data = [
                    position.to_dict()
                    for position in self.closed_positions[-1000:]
                ]
                with open(self.closed_positions_file, 'w') as f:
                    json.dump(closed_data, f, indent=2)
                
                # Save stats
                stats = {
                    'total_trades': self.total_trades,
                    'winning_trades': self.winning_trades,
                    'losing_trades': self.losing_trades
                }
                with open(self.stats_file, 'w') as f:
                    json.dump(stats, f, indent=2)
                
                logger.debug('Saved data to files')
                
            except Exception as e:
                logger.error(f'Error saving data to files: {e}')

    def open_position(self, token: str, mint: str, entry_price: float, amount_sol: float,
                     token_amount: float, platform: str, liquidity_usdt: float) -> Position:
        """Open a new position"""
        position = Position(token, mint, entry_price, amount_sol, token_amount, platform, liquidity_usdt)
        self.active_positions[mint] = position
        self.total_trades += 1
        logger.info(f'Opened position: {token} ({mint})')
        
        # Save to file
        self.save_to_files()
        
        return position

    def close_position(self, mint: str, exit_price: float, reason: str) -> Optional[Position]:
        """Close an active position"""
        if mint in self.active_positions:
            position = self.active_positions[mint]
            position.close(exit_price, reason)
            
            if position.pnl_sol > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1

            self.closed_positions.append(position)
            del self.active_positions[mint]
            
            logger.info(f'Closed position: {position.token} - PnL: {position.pnl_sol:.4f} SOL ({position.pnl_percent:.2f}%) - Reason: {reason}')
            
            # Save to file
            self.save_to_files()
            
            return position
        return None

    def get_position(self, mint: str) -> Optional[Position]:
        """Get active position by mint"""
        return self.active_positions.get(mint)

    def get_all_active(self) -> List[Position]:
        """Get all active positions"""
        return list(self.active_positions.values())

    def get_recent_closed(self, limit: int = 20) -> List[Position]:
        """Get recent closed positions"""
        return self.closed_positions[-limit:]

    def get_stats(self) -> dict:
        """Get trading statistics"""
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        total_pnl = sum(pos.pnl_sol for pos in self.closed_positions)
        
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_pnl_sol': total_pnl,
            'active_positions': len(self.active_positions)
        }
