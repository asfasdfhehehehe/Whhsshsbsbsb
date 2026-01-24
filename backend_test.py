import requests
import sys
import json
import time
from datetime import datetime

class SolanaTradingBotTester:
    def __init__(self, base_url="https://solana-trader-26.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=10):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                except:
                    print(f"   Response: {response.text[:200]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")

            self.test_results.append({
                'name': name,
                'success': success,
                'status_code': response.status_code,
                'expected_status': expected_status,
                'response_preview': response.text[:100] if not success else 'OK'
            })

            return success, response.json() if success and response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                'name': name,
                'success': False,
                'error': str(e)
            })
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_bot_status(self):
        """Test bot status endpoint"""
        return self.run_test("Bot Status", "GET", "bot/status", 200)

    def test_bot_start(self):
        """Test starting the bot"""
        config_data = {
            "action": "start",
            "config": {
                "private_key": "4kdnHjgYy7eDwdm2TZKth8Kf5mtFdx5FSFniJkaaBJH7NYdemfpBn7WApAXQst4KmFhrgfs1QmsebiZhHqVdTLUt",
                "amount_per_trade": 0.1,
                "take_profit_percent": 12.0,
                "stop_loss_percent": 30.0,
                "time_exit_minutes": 6,
                "liquidity_drop_percent": 30.0,
                "slippage": 5.0,
                "paper_trading": True
            }
        }
        return self.run_test("Start Bot", "POST", "bot/control", 200, config_data)

    def test_bot_stop(self):
        """Test stopping the bot"""
        stop_data = {"action": "stop"}
        return self.run_test("Stop Bot", "POST", "bot/control", 200, stop_data)

    def test_active_positions(self):
        """Test getting active positions"""
        return self.run_test("Active Positions", "GET", "positions/active", 200)

    def test_closed_positions(self):
        """Test getting closed positions"""
        return self.run_test("Closed Positions", "GET", "positions/closed", 200)

    def test_stats(self):
        """Test getting trading stats"""
        return self.run_test("Trading Stats", "GET", "stats", 200)

    def test_node_service_health(self):
        """Test Node.js trading service health"""
        try:
            response = requests.get("http://localhost:8002/health", timeout=5)
            if response.status_code == 200:
                print("✅ Node.js trading service is healthy")
                return True
            else:
                print(f"❌ Node.js service health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Node.js service health check error: {e}")
            return False

def main():
    print("🚀 Starting Solana Trading Bot API Tests")
    print("=" * 50)
    
    tester = SolanaTradingBotTester()
    
    # Test sequence
    tests = [
        ("Root API", tester.test_root_endpoint),
        ("Bot Status (Initial)", tester.test_bot_status),
        ("Active Positions", tester.test_active_positions),
        ("Closed Positions", tester.test_closed_positions),
        ("Trading Stats", tester.test_stats),
        ("Start Bot (Paper Trading)", tester.test_bot_start),
        ("Bot Status (After Start)", tester.test_bot_status),
        ("Stop Bot", tester.test_bot_stop),
        ("Bot Status (After Stop)", tester.test_bot_status),
    ]
    
    # Run backend API tests
    for test_name, test_func in tests:
        try:
            test_func()
            time.sleep(0.5)  # Small delay between tests
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
    
    # Test Node.js service
    print(f"\n🔍 Testing Node.js Trading Service...")
    node_healthy = tester.test_node_service_health()
    
    # Print summary
    print(f"\n📊 Test Results Summary")
    print("=" * 50)
    print(f"Tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "0%")
    print(f"Node.js service: {'✅ Healthy' if node_healthy else '❌ Unhealthy'}")
    
    # Print failed tests
    failed_tests = [t for t in tester.test_results if not t['success']]
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for test in failed_tests:
            error_msg = test.get('error', f'Status {test.get("status_code", "unknown")}')
            print(f"  - {test['name']}: {error_msg}")
    
    return 0 if tester.tests_passed == tester.tests_run and node_healthy else 1

if __name__ == "__main__":
    sys.exit(main())