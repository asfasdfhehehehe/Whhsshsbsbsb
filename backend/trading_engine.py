import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import logging
from position_manager import PositionManager, Position

logger = logging.getLogger(__name__)

class TradingEngine:
    def __init__(self, position_manager: PositionManager, config: dict):
        self.position_manager = position_manager
        self.config = config
        self.private_key = config.get('private_key', '')
        self.amount_per_trade = config.get('amount_per_trade', 0.1)
        self.take_profit_percent = config.get('take_profit_percent', 12)
        self.stop_loss_percent = config.get('stop_loss_percent', 30)
        self.time_exit_minutes = config.get('time_exit_minutes', 6)
        self.liquidity_drop_percent = config.get('liquidity_drop_percent', 30)
        self.slippage = config.get('slippage', 5)
        self.paper_trading = config.get('paper_trading', True)
        self.running = False
        self.node_service_url = 'http://localhost:8002'

    async def execute_trade(self, direction: str, mint: str, amount: float, platform: str, pool_address: str = None) -> dict:
        """Execute trade via Node.js service or simulate in paper trading mode"""
        if self.paper_trading:
            # Paper trading simulation
            logger.info(f'PAPER TRADE: {direction} {amount} SOL of {mint} on platform {platform}')
            return {
                'success': True,
                'signature': f'paper_{datetime.now(timezone.utc).timestamp()}',
                'paper': True
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'direction': direction,
                    'mint': mint,
                    'amount': amount,
                    'slippage': self.slippage,
                    'privateKey': self.private_key,
                    'platform': platform,
                    'poolAddress': pool_address
                }
                
                async with session.post(
                    f'{self.node_service_url}/api/node/trade',
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f'Trade execution failed: {error_text}')
                        return {'success': False, 'error': error_text}
        except Exception as e:
            logger.error(f'Error executing trade: {e}')
            return {'success': False, 'error': str(e)}

    async def batch_buy_tokens(self, tokens: List[Dict]) -> List[dict]:
        """Batch buy multiple tokens (max 2)"""
        if not tokens:
            return []

        tokens_to_buy = tokens[:2]  # Limit to 2 tokens
        results = []

        if self.paper_trading:
            for token in tokens_to_buy:
                result = await self.execute_trade(
                    'buy',
                    token['token'],
                    self.amount_per_trade,
                    token.get('platform', '1')
                )
                results.append(result)
        else:
            # Real batch trade
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {
                        'tokens': [{'mint': t['token'], 'platform': t.get('platform', '1')} for t in tokens_to_buy],
                        'privateKey': self.private_key,
                        'amount': self.amount_per_trade,
                        'slippage': self.slippage
                    }
                    
                    async with session.post(
                        f'{self.node_service_url}/api/node/batch-trade',
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            results = data.get('results', [])
            except Exception as e:
                logger.error(f'Batch trade error: {e}')

        return results

    async def process_new_tokens(self, tokens: List[Dict], broadcast_callback=None):
        """Process new tokens and execute buys"""
        if not self.running or not tokens:
            return

        logger.info(f'Processing {len(tokens)} new tokens')
        
        # Execute batch buy
        results = await self.batch_buy_tokens(tokens)

        # Open positions for successful trades
        for i, token in enumerate(tokens[:len(results)]):
            if i < len(results) and results[i].get('success'):
                price = float(token.get('price', 0))
                token_amount = self.amount_per_trade / price if price > 0 else 0
                
                position = self.position_manager.open_position(
                    token=token.get('code', 'UNKNOWN'),
                    mint=token['token'],
                    entry_price=price,
                    amount_sol=self.amount_per_trade,
                    token_amount=token_amount,
                    platform=token.get('poolName', 'Unknown'),
                    liquidity_usdt=float(token.get('liquidityUsdt', 0))
                )
                
                # Broadcast trade event
                if broadcast_callback:
                    await broadcast_callback({
                        'type': 'trade',
                        'data': {
                            'action': 'buy',
                            'token': position.token,
                            'mint': position.mint,
                            'price': price,
                            'amount': self.amount_per_trade,
                            'mode': 'paper' if self.paper_trading else 'live'
                        }
                    })

    async def monitor_positions(self, current_tokens: List[Dict], broadcast_callback=None):
        """Monitor active positions and execute exit conditions"""
        if not self.running:
            return

        # Create price lookup from current tokens
        price_lookup = {token['token']: token for token in current_tokens}
        current_time = datetime.now(timezone.utc)

        positions_to_close = []

        for mint, position in self.position_manager.active_positions.items():
            if mint not in price_lookup:
                continue

            token_data = price_lookup[mint]
            current_price = float(token_data.get('price', 0))
            current_liquidity = float(token_data.get('liquidityUsdt', 0))

            if current_price == 0:
                continue

            # Calculate current PnL
            pnl_sol, pnl_percent = position.calculate_pnl(current_price)

            # Check exit conditions
            exit_reason = None

            # Take Profit
            if pnl_percent >= self.take_profit_percent:
                exit_reason = f'Take Profit ({pnl_percent:.2f}%)'

            # Stop Loss
            elif pnl_percent <= -self.stop_loss_percent:
                exit_reason = f'Stop Loss ({pnl_percent:.2f}%)'

            # Time-based exit
            elif (current_time - position.entry_time) > timedelta(minutes=self.time_exit_minutes):
                exit_reason = f'Time Exit ({self.time_exit_minutes}min)'

            # Liquidity drop
            elif position.entry_liquidity > 0:
                liquidity_percent = (current_liquidity / position.entry_liquidity) * 100
                if liquidity_percent < (100 - self.liquidity_drop_percent):
                    exit_reason = f'Liquidity Drop ({liquidity_percent:.1f}%)'

            if exit_reason:
                positions_to_close.append((mint, current_price, exit_reason, token_data))

        # Execute closes
        for mint, exit_price, reason, token_data in positions_to_close:
            # Execute sell
            result = await self.execute_trade(
                'sell',
                mint,
                self.position_manager.active_positions[mint].token_amount,
                token_data.get('platform', '1')
            )

            if result.get('success'):
                closed_position = self.position_manager.close_position(mint, exit_price, reason)
                
                # Broadcast position closed event
                if broadcast_callback and closed_position:
                    await broadcast_callback({
                        'type': 'position_closed',
                        'data': closed_position.to_dict()
                    })

    def update_config(self, config: dict):
        """Update trading configuration"""
        self.config.update(config)
        self.amount_per_trade = config.get('amount_per_trade', self.amount_per_trade)
        self.take_profit_percent = config.get('take_profit_percent', self.take_profit_percent)
        self.stop_loss_percent = config.get('stop_loss_percent', self.stop_loss_percent)
        self.time_exit_minutes = config.get('time_exit_minutes', self.time_exit_minutes)
        self.liquidity_drop_percent = config.get('liquidity_drop_percent', self.liquidity_drop_percent)
        self.slippage = config.get('slippage', self.slippage)
        self.paper_trading = config.get('paper_trading', self.paper_trading)
        self.private_key = config.get('private_key', self.private_key)

    def start(self):
        """Start the trading engine"""
        self.running = True
        logger.info('Trading engine started')

    def stop(self):
        """Stop the trading engine"""
        self.running = False
        logger.info('Trading engine stopped')
