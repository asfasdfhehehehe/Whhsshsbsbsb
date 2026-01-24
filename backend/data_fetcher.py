import asyncio
import aiohttp
import json
from datetime import datetime, timezone
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class DataFetcher:
    def __init__(self):
        self.api_url = 'https://b.alph.ai/smart-web-gateway/snipe/list/graduated/sol'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=utf-8',
            'Referer': 'https://alph.ai/',
            'exchange-client': 'pc',
            'Origin': 'https://alph.ai',
        }
        self.cookies = {
            '_ga_L8PCZLCK8N': 'GS1.1.1766474898.25.1.1766474898.60.0.0',
            '_ga': 'GA1.1.1606631668.1765366062',
        }
        self.session: Optional[aiohttp.ClientSession] = None
        self.seen_tokens = set()  # Anti-duplicate tracking

    async def start(self):
        """Initialize aiohttp session"""
        self.session = aiohttp.ClientSession()

    async def stop(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    async def fetch_tokens(self) -> List[Dict]:
        """Fetch tokens from alph.ai API"""
        try:
            json_data = {
                'language': 'en_US',
                'platform': 'All',
            }

            async with self.session.post(
                self.api_url,
                headers=self.headers,
                cookies=self.cookies,
                json=json_data,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', []) if isinstance(data, dict) else data
                else:
                    logger.error(f'API request failed: {response.status}')
                    return []
        except Exception as e:
            logger.error(f'Error fetching tokens: {e}')
            return []

    def filter_new_tokens(self, tokens: List[Dict], max_age_seconds: int = 10) -> List[Dict]:
        """Filter tokens by age and remove duplicates"""
        current_time = datetime.now(timezone.utc).timestamp() * 1000  # Convert to milliseconds
        filtered_tokens = []

        for token in tokens:
            token_address = token.get('token')
            token_age_ms = token.get('age', 0)

            # Skip if already seen
            if token_address in self.seen_tokens:
                continue

            # Filter by age (convert max_age_seconds to milliseconds)
            if token_age_ms < (max_age_seconds * 1000):
                filtered_tokens.append(token)
                self.seen_tokens.add(token_address)
                logger.info(f'New token found: {token_address} (age: {token_age_ms}ms)')

        return filtered_tokens

    async def continuous_fetch(self, callback, interval_ms: int = 100):
        """Continuously fetch tokens at specified interval"""
        logger.info(f'Starting continuous fetch (interval: {interval_ms}ms)')
        
        while True:
            try:
                tokens = await self.fetch_tokens()
                if tokens:
                    new_tokens = self.filter_new_tokens(tokens)
                    if new_tokens:
                        await callback(new_tokens)
                
                await asyncio.sleep(interval_ms / 1000)  # Convert ms to seconds
            except Exception as e:
                logger.error(f'Error in continuous fetch: {e}')
                await asyncio.sleep(1)  # Wait before retrying
