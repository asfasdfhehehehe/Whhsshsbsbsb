from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging

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

class PositionManager:
    def __init__(self):
        self.active_positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

    def open_position(self, token: str, mint: str, entry_price: float, amount_sol: float,
                     token_amount: float, platform: str, liquidity_usdt: float) -> Position:
        """Open a new position"""
        position = Position(token, mint, entry_price, amount_sol, token_amount, platform, liquidity_usdt)
        self.active_positions[mint] = position
        self.total_trades += 1
        logger.info(f'Opened position: {token} ({mint})')
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
