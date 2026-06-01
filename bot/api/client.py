import logging
import aiohttp
from typing import Optional, Dict, Any
from bot.config import settings

logger = logging.getLogger(__name__)

class ExternalAPIClient:
    """
    Asynchronous client interface interacting with the external payment gateway and 2FA server.
    Leverages connection pooling to minimize round-trip latency.
    """
    def __init__(self, base_url: str = settings.external_api_url, token: str = settings.external_api_token):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self._session: Optional[aiohttp.ClientSession] = None

    def get_session(self) -> aiohttp.ClientSession:
        """
        Lazy initialization of the ClientSession connection pool.
        Ensures TCP socket re-use for optimized outbound high-throughput connections.
        """
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
            self._session = aiohttp.ClientSession(connector=connector, headers=self._headers)
        return self._session

    async def close(self):
        """Gracefully tears down the network connection pool during application shutdown."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def check_hash(self, telegram_id: int, hash_password: str) -> Optional[str]:
        """
        Validates account linkage secret hash key on the main marketplace site.
        Returns corresponding marketplace site_login username if valid, otherwise None.
        """
        url = f"{self.base_url}/api/v1/auth/check-hash"
        payload = {"telegram_id": telegram_id, "hash_password": hash_password}
        
        try:
            session = self.get_session()
            async with session.post(url, json=payload, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return data.get("site_login")
                    logger.warning(f"Hash validation rejected by marketplace API: {data.get('message')}")
                else:
                    logger.error(f"Failed to link hash, HTTP status: {response.status}")
        except Exception as e:
            logger.error(f"Failed to connect to check-hash API endpoint: {e}")
            
            # Robust local environment fallbacks when debugging without internet connectivity
            if settings.debug:
                logger.info("Active account linking mockup response triggered (DEBUG mode)")
                if hash_password.lower().startswith("error") or len(hash_password) < 4:
                    return None
                return f"user_{telegram_id % 10000}"
                
        return None

    async def create_invoice(self, telegram_id: int, cryptocurrency: str) -> Optional[Dict[str, Any]]:
        """
        Requests new custom payment invoice address token from external gateway client API.
        Returns a dictionary containing wallet info and replenishment limits, otherwise None.
        """
        url = f"{self.base_url}/api/v1/billing/create-invoice"
        payload = {"telegram_id": telegram_id, "cryptocurrency": cryptocurrency.upper()}
        
        try:
            session = self.get_session()
            async with session.post(url, json=payload, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return {
                            "address": data.get("address"),
                            "min_amount": float(data.get("min_amount", 15.0))
                        }
                logger.error(f"Failed to compile payment invoice request, HTTP status: {response.status}")
        except Exception as e:
            logger.error(f"Failed to connect to create-invoice API endpoint: {e}")
            
            # Local debug simulation of invoice generation for development testing
            if settings.debug:
                logger.info("Active payment coin mock addresses triggered (DEBUG mode)")
                mock_addresses = {
                    "BTC": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                    "USDT_TRC20": "TR7NHqju6E4yfC15f5dssC21t7D6xdS7yQ",
                    "USDT_ERC20": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
                    "USDC_ERC20": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                    "LTC": "M8T1vQBBCEomRRt54Wj6Zwyb9aCpPQ3MQi",
                    "ETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
                }
                coin = cryptocurrency.upper()
                if coin not in mock_addresses:
                    if "TRC20" in coin or "TRC-20" in coin:
                        coin = "USDT_TRC20"
                    elif "ERC20" in coin or "ERC-20" in coin:
                        if "USDC" in coin:
                            coin = "USDC_ERC20"
                        else:
                            coin = "USDT_ERC20"
                    elif "LITECOIN" in coin:
                        coin = "LTC"
                    elif "BITCOIN" in coin:
                        coin = "BTC"
                
                return {
                    "address": mock_addresses.get(coin, "0x0000000000000000000000000000000000000000"),
                    "min_amount": 15.0
                }
                
        return None

    async def get_2fa_code(self, telegram_id: int) -> Optional[str]:
        """
        Retrieves active marketplace 2FA authorization token.
        """
        url = f"{self.base_url}/api/v1/auth/2fa"
        payload = {"telegram_id": telegram_id}
        
        try:
            session = self.get_session()
            async with session.post(url, json=payload, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return str(data.get("code"))
                logger.error(f"Failed to fetch active 2FA key, HTTP status: {response.status}")
        except Exception as e:
            logger.error(f"Failed to connect to 2FA endpoint: {e}")
            
            # Generate random temporary mock code on local PC to verify the user experience
            if settings.debug:
                logger.info("Active random mock 2FA code generated (DEBUG mode)")
                import random
                return "".join(random.choices("0123456789", k=6))
                
        return None

api_client = ExternalAPIClient()

