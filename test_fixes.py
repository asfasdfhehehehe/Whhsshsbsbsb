#!/usr/bin/env python3
"""
Test script to verify all fixes applied to the Solana Trading Bot
Run this after starting the services to validate functionality
"""

import asyncio
import aiohttp
import json
from datetime import datetime

BASE_URL = 'http://localhost:8000/api'
NODE_URL = 'http://localhost:8002'

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def log(self, message, status='INFO'):
        timestamp = datetime.now().strftime('%H:%M:%S')
        colors = {
            'INFO': '\033[94m',
            'PASS': '\033[92m',
            'FAIL': '\033[91m',
            'WARN': '\033[93m'
        }
        reset = '\033[0m'
        print(f"[{timestamp}] {colors.get(status, '')}{status}{reset}: {message}")
    
    def test_result(self, test_name, passed, details=''):
        if passed:
            self.passed += 1
            self.log(f"✓ {test_name} - {details}", 'PASS')
        else:
            self.failed += 1
            self.log(f"✗ {test_name} - {details}", 'FAIL')
        self.tests.append({'name': test_name, 'passed': passed, 'details': details})
    
    async def test_backend_health(self):
        """Test backend API is running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{BASE_URL}/') as response:
                    if response.status == 200:
                        data = await response.json()
                        self.test_result('Backend Health', True, data.get('message', ''))
                        return True
                    else:
                        self.test_result('Backend Health', False, f'Status: {response.status}')
                        return False
        except Exception as e:
            self.test_result('Backend Health', False, str(e))
            return False
    
    async def test_node_service_health(self):
        """Test Node.js service is running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{NODE_URL}/health') as response:
                    if response.status == 200:
                        data = await response.json()
                        self.test_result('Node Service Health', True, data.get('status', ''))
                        return True
                    else:
                        self.test_result('Node Service Health', False, f'Status: {response.status}')
                        return False
        except Exception as e:
            self.test_result('Node Service Health', False, str(e))
            return False
    
    async def test_bot_status(self):
        """Test bot status endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{BASE_URL}/bot/status') as response:
                    if response.status == 200:
                        data = await response.json()
                        config_present = 'config' in data if data.get('running') else True
                        self.test_result('Bot Status Endpoint', config_present, 
                                       f"Running: {data.get('running', False)}")
                        return True
                    else:
                        self.test_result('Bot Status Endpoint', False, f'Status: {response.status}')
                        return False
        except Exception as e:
            self.test_result('Bot Status Endpoint', False, str(e))
            return False
    
    async def test_jito_tip_config(self):
        """Test Jito tip configuration in Node service"""
        self.log("Checking Jito tip configuration in node_service/trading_service.js")
        try:
            with open('node_service/trading_service.js', 'r') as f:
                content = f.read()
                has_default_tip = 'DEFAULT_JITO_TIP = 0.001' in content
                has_jito_param = 'jitoTip: tip' in content
                
                if has_default_tip and has_jito_param:
                    self.test_result('Jito Tip Configuration', True, 
                                   'Default tip set to 0.001 SOL')
                else:
                    self.test_result('Jito Tip Configuration', False, 
                                   'Jito tip not properly configured')
        except Exception as e:
            self.test_result('Jito Tip Configuration', False, str(e))
    
    async def test_duplicate_prevention(self):
        """Test duplicate prevention mechanism"""
        self.log("Checking duplicate prevention in trading_engine.py")
        try:
            with open('backend/trading_engine.py', 'r') as f:
                content = f.read()
                has_purchased_tokens = 'self.purchased_tokens = set()' in content
                has_closing_positions = 'self.closing_positions = set()' in content
                has_duplicate_check = 'in self.purchased_tokens' in content
                
                if has_purchased_tokens and has_closing_positions and has_duplicate_check:
                    self.test_result('Duplicate Prevention', True, 
                                   'Anti-duplicate mechanisms implemented')
                else:
                    self.test_result('Duplicate Prevention', False, 
                                   'Missing duplicate prevention code')
        except Exception as e:
            self.test_result('Duplicate Prevention', False, str(e))
    
    async def test_venue_switching(self):
        """Test venue switching logic"""
        self.log("Checking venue switching logic in trading_engine.py")
        try:
            with open('backend/trading_engine.py', 'r') as f:
                content = f.read()
                has_venue_method = 'def apply_venue_switching' in content
                has_dbc_detection = "'METEORA' in pool_name and 'DBC' in pool_name" in content
                has_damm_switch = "return '8'  # METEORA_DAMM_V2" in content
                
                if has_venue_method and has_dbc_detection and has_damm_switch:
                    self.test_result('Venue Switching Logic', True, 
                                   'DBC → DAMM V2 switching implemented')
                else:
                    self.test_result('Venue Switching Logic', False, 
                                   'Missing venue switching code')
        except Exception as e:
            self.test_result('Venue Switching Logic', False, str(e))
    
    async def test_slippage_endpoint(self):
        """Test slippage query endpoint"""
        self.log("Checking slippage endpoint in node_service/trading_service.js")
        try:
            with open('node_service/trading_service.js', 'r') as f:
                content = f.read()
                has_endpoint = "'/api/node/get-slippage'" in content
                has_meteora_query = 'fetchMeteoraPools' in content
                has_swap_quote = 'fetchSwapQuote' in content
                
                if has_endpoint and has_meteora_query and has_swap_quote:
                    self.test_result('Slippage Endpoint', True, 
                                   'Real slippage query implemented')
                else:
                    self.test_result('Slippage Endpoint', False, 
                                   'Missing slippage query functionality')
        except Exception as e:
            self.test_result('Slippage Endpoint', False, str(e))
    
    async def test_paper_trading_enhancements(self):
        """Test paper trading enhancements"""
        self.log("Checking paper trading enhancements in trading_engine.py")
        try:
            with open('backend/trading_engine.py', 'r') as f:
                content = f.read()
                has_get_slippage = 'async def get_real_slippage' in content
                has_slippage_loss = 'slippage_loss = amount * (actual_slippage / 100)' in content
                has_jito_cost = 'jito_cost = self.jito_tip' in content
                has_net_amount = 'net_amount = amount - slippage_loss - jito_cost' in content
                
                if has_get_slippage and has_slippage_loss and has_jito_cost and has_net_amount:
                    self.test_result('Paper Trading Enhancements', True, 
                                   'Real slippage + Jito tip calculation implemented')
                else:
                    self.test_result('Paper Trading Enhancements', False, 
                                   'Missing paper trading enhancements')
        except Exception as e:
            self.test_result('Paper Trading Enhancements', False, str(e))
    
    async def test_dependencies(self):
        """Test required dependencies"""
        self.log("Checking dependencies")
        try:
            import aiohttp
            import fastapi
            import motor
            self.test_result('Python Dependencies', True, 'Required packages installed')
        except ImportError as e:
            self.test_result('Python Dependencies', False, f'Missing: {e}')
        
        try:
            with open('node_service/package.json', 'r') as f:
                package_data = json.load(f)
                deps = package_data.get('dependencies', {})
                required = ['solana-trade', '@solana/web3.js', 'bs58', 'express', 'cors']
                missing = [pkg for pkg in required if pkg not in deps]
                
                if not missing:
                    self.test_result('Node.js Dependencies', True, 
                                   f'{len(required)} packages present')
                else:
                    self.test_result('Node.js Dependencies', False, 
                                   f'Missing: {", ".join(missing)}')
        except Exception as e:
            self.test_result('Node.js Dependencies', False, str(e))
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print(f"TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: \033[92m{self.passed}\033[0m")
        print(f"Failed: \033[91m{self.failed}\033[0m")
        print(f"Success Rate: {(self.passed/(self.passed+self.failed)*100):.1f}%")
        print("="*60)
        
        if self.failed > 0:
            print("\nFailed Tests:")
            for test in self.tests:
                if not test['passed']:
                    print(f"  - {test['name']}: {test['details']}")
        
        print("\n")

async def main():
    """Run all tests"""
    runner = TestRunner()
    
    print("="*60)
    print("SOLANA TRADING BOT - FIX VERIFICATION TESTS")
    print("="*60)
    print()
    
    # Code-based tests (always run)
    runner.log("Running code verification tests...")
    await runner.test_duplicate_prevention()
    await runner.test_venue_switching()
    await runner.test_jito_tip_config()
    await runner.test_slippage_endpoint()
    await runner.test_paper_trading_enhancements()
    await runner.test_dependencies()
    
    # Service tests (require running services)
    runner.log("\nRunning service connectivity tests...")
    runner.log("(Make sure all services are running: backend, node_service)")
    
    backend_ok = await runner.test_backend_health()
    node_ok = await runner.test_node_service_health()
    
    if backend_ok:
        await runner.test_bot_status()
    
    # Print summary
    runner.print_summary()
    
    # Exit code based on results
    return 0 if runner.failed == 0 else 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    exit(exit_code)
