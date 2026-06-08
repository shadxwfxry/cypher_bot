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

    def get_timeout(self) -> float:
        """
        Returns connection timeout, adjusting for Tor network latency if onion address.
        """
        if ".onion" in self.base_url:
            return 30.0 # High latency Tor network timeout
        return 10.0

    def get_session(self) -> aiohttp.ClientSession:
        """
        Lazy initialization of the ClientSession connection pool.
        Ensures TCP socket re-use for optimized outbound high-throughput connections,
        routing through SOCKS5 Tor proxy for .onion domains.
        """
        if self._session is None or self._session.closed:
            connector = None
            if ".onion" in self.base_url:
                try:
                    from aiohttp_socks import ProxyConnector
                    connector = ProxyConnector.from_url(settings.tor_proxy, limit=100)
                    logger.info(f"Tor SOCKS5 proxy connector initialized for .onion domain: {settings.tor_proxy}")
                except ImportError:
                    logger.warning("aiohttp-socks package not installed. Tor proxy routing might not work.")
            
            if connector is None:
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
            async with session.post(url, json=payload, timeout=self.get_timeout()) as response:
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
            async with session.post(url, json=payload, timeout=self.get_timeout()) as response:
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
            async with session.post(url, json=payload, timeout=self.get_timeout()) as response:
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

    async def get_products(self, category: str) -> Optional[list[dict[str, Any]]]:
        """
        Fetches products in a specific category from the website.
        """
        url = f"{self.base_url}/api/v1/catalog/products"
        params = {"category": category}
        try:
            session = self.get_session()
            async with session.get(url, params=params, timeout=self.get_timeout()) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return data.get("products", [])
                logger.error(f"Failed to fetch catalog products, HTTP status: {response.status}")
        except Exception as e:
            logger.error(f"Failed to connect to catalog products endpoint: {e}")
            
            # Local debug mock implementation
            if settings.debug:
                logger.info(f"Active mockup products for category '{category}' triggered (DEBUG mode)")
                mock_data = {
                    "accounts": [
                        {"id": "acc_netflix", "name": "💎 Netflix Premium 4K", "price": 5.00, "desc": "1 Month Ultra HD Account"},
                        {"id": "acc_spotify", "name": "💎 Spotify Premium 1 Year", "price": 10.00, "desc": "12 Months Individual Plan"},
                        {"id": "acc_chatgpt", "name": "💎 ChatGPT Plus Account", "price": 22.00, "desc": "GPT-4 Access with API key"}
                    ],
                    "documents": [
                        {"id": "doc_usa_pass", "name": "📁 USA Passport Scan", "price": 15.00, "desc": "High quality scanned copy"},
                        {"id": "doc_uk_bill", "name": "📁 UK Utility Bill PDF", "price": 12.00, "desc": "Editable PDF utility bill"}
                    ],
                    "self_reg": [
                        {"id": "sreg_wise", "name": "⚙️ Wise Self-Reg Guide", "price": 25.00, "desc": "Full step by step guide"},
                        {"id": "sreg_revolut", "name": "⚙️ Revolut Account Guide", "price": 30.00, "desc": "Bypass verification guide"}
                    ],
                    "fullz": [
                        {"id": "fz_usa", "name": "🪪 SSN+DOB USA Fullz", "price": 8.00, "desc": "Clean credit history leads"}
                    ],
                    "lookup": [
                        {"id": "lk_bg", "name": "🔍 Background Check Report", "price": 20.00, "desc": "Full report from US search"}
                    ]
                }
                return mock_data.get(category, [])
        return None

    async def buy_product(self, telegram_id: int, product_id: str) -> Optional[dict[str, Any]]:
        """
        Executes a balance purchase on the main marketplace site via API.
        Sends: POST /api/v1/marketplace/buy
        Payload: {"telegram_id": telegram_id, "product_id": product_id}
        Returns: product payload/details (e.g. {"status": "success", "license_key": "..."}) or None
        """
        url = f"{self.base_url}/api/v1/marketplace/buy"
        payload = {"telegram_id": telegram_id, "product_id": product_id}
        
        try:
            session = self.get_session()
            async with session.post(url, json=payload, timeout=self.get_timeout()) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return data
                logger.error(f"Failed to execute buy_product, HTTP status: {response.status}")
        except Exception as e:
            logger.error(f"Failed to connect to buy_product API endpoint: {e}")
            
            # Local debug mock implementation
            if settings.debug:
                logger.info(f"Active mockup purchase for product_id '{product_id}' triggered (DEBUG mode)")
                import uuid
                mock_keys = {
                    "acc_netflix": "Netflix Account Profile 4 Credentials: \n📧 netflix_prem_sub72@gmail.com:Pass4netflix!",
                    "acc_spotify": "Spotify Premium Individual Link: \n🔗 https://spotify.com/us/family/join/invite/51a2f9b8c772ee8a",
                    "acc_chatgpt": "ChatGPT Plus API Access Token: \n🔑 sk-proj-CypherMarketSecretToken12093840294830192",
                    "doc_usa_pass": "USA Passport Scan Copy File: \n📁 Download URL: https://cypher-market.host/files/vault/doc_scan_8829a.pdf",
                    "doc_uk_bill": "UK Utility Bill Editable Template: \n📁 Download URL: https://cypher-market.host/files/vault/uk_utility_bill_template.zip",
                    "sreg_wise": "Wise Self-Reg Complete Guidebook: \n📁 Download URL: https://cypher-market.host/files/guides/wise_self_reg_2026.pdf",
                    "sreg_revolut": "Revolut Bypass Guidebook: \n📁 Download URL: https://cypher-market.host/files/guides/revolut_bypass_guide.pdf",
                    "fz_usa": "SSN+DOB USA Lead Record:\n👤 Name: Michael Smith\n📍 Address: 442 Pine Rd, Atlanta, GA\n🪪 SSN: 228-44-XXXX\n📅 DOB: 11/14/1984\n📞 Phone: +1 404-555-0193",
                    "lk_bg": "Lookup Background Check PDF:\n📁 Search Report ID: #bg-99201-a9f\n🔗 Download URL: https://cypher-market.host/files/reports/bg_report_99201.pdf"
                }
                # Reasonable dummy prices
                prices = {
                    "acc_netflix": 5.00,
                    "acc_spotify": 10.00,
                    "acc_chatgpt": 22.00,
                    "doc_usa_pass": 15.00,
                    "doc_uk_bill": 12.00,
                    "sreg_wise": 25.00,
                    "sreg_revolut": 30.00,
                    "fz_usa": 8.00,
                    "lk_bg": 20.00
                }
                return {
                    "status": "success",
                    "product_id": product_id,
                    "price": prices.get(product_id, 10.00),
                    "license_key": mock_keys.get(product_id, f"Mock license key delivered: \n🔑 cypher-key-{uuid.uuid4().hex[:12]}")
                }
        return None

api_client = ExternalAPIClient()

