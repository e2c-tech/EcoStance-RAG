"""
Web search tool for Ecommerce Agent.
Allowed topics: products, prices, brands, shopping, reviews, tech specs.
"""
import logging
from langchain.tools import tool
from agents.shared.web_search_base import execute_web_search

logger = logging.getLogger(__name__)

_ALLOWED_KEYWORDS = [
    "product", "item", "model", "specification", "feature", "release", "launch",
    "price", "cost", "rate", "discount", "offer", "deal", "cheap", "expensive",
    "brand", "manufacturer", "maker", "vendor", "supplier",
    "buy", "purchase", "order", "shop", "store", "amazon", "flipkart",
    "review", "rating", "feedback", "comparison", "vs", "best", "worst",
    "specs", "processor", "ram", "storage", "battery", "display", "resolution",
    "warranty", "return policy", "refund", "shipping cost",
]


def _is_allowed(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in _ALLOWED_KEYWORDS)


def create_web_search_tool():
    @tool
    def web_search(query: str) -> str:
        """
        Search the web for product information, prices, brand details,
        reviews, or shopping-related queries not in the database or knowledge base.
        """
        if not _is_allowed(query):
            logger.warning(f"Ecommerce agent web search blocked (off-topic): {query[:80]}")
            return (
                "I can only search for product, price, brand, or shopping-related topics. "
                "Please refine your query."
            )
        return execute_web_search(query)

    return web_search
