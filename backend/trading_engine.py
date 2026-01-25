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
        
        # Anti-duplicate tracking
        self.purchased_tokens = set()  # Track tokens that have been purchased
        self.closing_positions = set()  # Track positions being closed to prevent duplicate sells
        self.jito_tip = 0.001  # Default Jito tip in SOL

    async def get_real_slippage(self, mint: str, amount: float, direction: str, platform: str) -> dict:
        """Get real slippage from Meteora for paper trading"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'mint': mint,
                    'amount': amount,
                    'direction': direction,
                    'slippage': self.slippage,
                    'platform': platform
                }
                
                async with session.post(
                    f'{self.node_service_url}/api/node/get-slippage',
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f'Failed to get real slippage, using default')
                        return {'slippage': self.slippage, 'success': False}
        except Exception as e:
            logger.error(f'Error getting slippage: {e}')
            return {'slippage': self.slippage, 'success': False}

    async def execute_trade(self, direction: str, mint: str, amount: float, platform: str, pool_address: str = None) -> dict:
        """Execute trade via Node.js service or simulate in paper trading mode"""
        if self.paper_trading:
            # Get real slippage for paper trading
            slippage_data = await self.get_real_slippage(mint, amount, direction, platform)
            actual_slippage = slippage_data.get('slippage', self.slippage)
            
            # Calculate realistic execution with slippage and Jito tip
            slippage_loss = amount * (actual_slippage / 100)
            jito_cost = self.jito_tip
            net_amount = amount - slippage_loss - jito_cost
            
            logger.info(f'PAPER TRADE: {direction} {amount} SOL of {mint} on platform {platform}')
            logger.info(f'  Slippage: {actual_slippage}% (-{slippage_loss:.6f} SOL)')
            logger.info(f'  Jito Tip: -{jito_cost:.6f} SOL')
            logger.info(f'  Net Amount: {net_amount:.6f} SOL')
            
            return {
                'success': True,
                'signature': f'paper_{datetime.now(timezone.utc).timestamp()}',
                'paper': True,
                'slippage': actual_slippage,
                'slippage_loss': slippage_loss,
                'jito_tip': jito_cost,
                'net_amount': net_amount
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
                    'poolAddress': pool_address,
                    'jitoTip': self.jito_tip  # Add Jito tip
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
                # Apply venue switching logic for Meteora DBC
                platform = self.apply_venue_switching(token)
                
                result = await self.execute_trade(
                    'buy',
                    token['token'],
                    self.amount_per_trade,
                    platform
                )
                results.append(result)
        else:
            # Real batch trade
            try:
                async with aiohttp.ClientSession() as session:
                    # Apply venue switching for each token
                    processed_tokens = []
                    for t in tokens_to_buy:
                        platform = self.apply_venue_switching(t)
                        processed_tokens.append({
                            'mint': t['token'], 
                            'platform': platform
                        })
                    
                    payload = {
                        'tokens': processed_tokens,
                        'privateKey': self.private_key,
                        'amount': self.amount_per_trade,
                        'slippage': self.slippage,
                        'jitoTip': self.jito_tip  # Add Jito tip
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

    def apply_venue_switching(self, token: Dict) -> str:
        """
        Apply venue switching logic: If token is on Meteora DBC, switch to DAMM V2
        Returns the platform code to use for trading
        """
        platform = token.get('platform', '1')
        pool_name = token.get('poolName', '').upper()
        
        # Check if token is on Meteora DBC
        # Meteora DBC typically identified by poolName containing 'METEORA' but not 'DAMM'
        # or platform code that indicates DBC (need to identify from API)
        if 'METEORA' in pool_name and 'DBC' in pool_name:
            logger.info(f'Token {token.get("token")} detected on Meteora DBC, switching to DAMM V2')
            return '8'  # METEORA_DAMM_V2
        
        # If already on DAMM V2, keep it
        if platform == '8':
            logger.info(f'Token {token.get("token")} already on DAMM V2')
            return '8'
        
        # For other platforms, use original
        return platform

    async def process_new_tokens(self, tokens: List[Dict], broadcast_callback=None):
        """Process new tokens and execute buys"""
        if not self.running or not tokens:
            return

        # Filter out tokens that have already been purchased (anti-duplicate)
        new_tokens = []
        for token in tokens:
            mint = token['token']
            if mint not in self.purchased_tokens and mint not in self.position_manager.active_positions:
                new_tokens.append(token)
            else:
                logger.info(f'Skipping duplicate token: {mint}')

        if not new_tokens:
            return

        logger.info(f'Processing {len(new_tokens)} new tokens')
        
        # Execute batch buy
        results = await self.batch_buy_tokens(new_tokens)

        # Open positions for successful trades
        for i, token in enumerate(new_tokens[:len(results)]):
            if i < len(results) and results[i].get('success'):
                mint = token['token']
                
                # Mark as purchased to prevent duplicates
                self.purchased_tokens.add(mint)
                
                price = float(token.get('price', 0))
                
                # Calculate effective amount after slippage and fees (for paper trading)
                effective_amount = self.amount_per_trade
                if self.paper_trading and 'net_amount' in results[i]:
                    effective_amount = results[i]['net_amount']
                
                token_amount = effective_amount / price if price > 0 else 0
                
                # Apply venue switching to get actual platform used
                platform_used = self.apply_venue_switching(token)
                
                position = self.position_manager.open_position(
                    token=token.get('code', 'UNKNOWN'),
                    mint=mint,
                    entry_price=price,
                    amount_sol=self.amount_per_trade,
                    token_amount=token_amount,
                    platform=token.get('poolName', 'Unknown') + f' (Platform: {platform_used})',
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
                            'mode': 'paper' if self.paper_trading else 'live',
                            'platform': platform_used,
                            'slippage': results[i].get('slippage', self.slippage) if self.paper_trading else None,
                            'jito_tip': results[i].get('jito_tip', self.jito_tip) if self.paper_trading else None
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
            # Skip if already being closed (prevent duplicate sells)
            if mint in self.closing_positions:
                continue
                
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
            # Mark as closing to prevent duplicate executions
            self.closing_positions.add(mint)
            
            try:
                # Apply venue switching for sell as well
                token_with_platform = {
                    'token': mint,
                    'platform': token_data.get('platform', '1'),
                    'poolName': token_data.get('poolName', '')
                }
                platform_to_use = self.apply_venue_switching(token_with_platform)
                
                # Execute sell
                result = await self.execute_trade(
                    'sell',
                    mint,
                    self.position_manager.active_positions[mint].token_amount,
                    platform_to_use
                )

                if result.get('success'):
                    closed_position = self.position_manager.close_position(mint, exit_price, reason)
                    
                    # Remove from purchased tokens so it can be bought again in future
                    if mint in self.purchased_tokens:
                        self.purchased_tokens.discard(mint)
                    
                    # Broadcast position closed event
                    if broadcast_callback and closed_position:
                        await broadcast_callback({
                            'type': 'position_closed',
                            'data': closed_position.to_dict()
                        })
            finally:
                # Always remove from closing set
                if mint in self.closing_positions:
                    self.closing_positions.discard(mint)

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
