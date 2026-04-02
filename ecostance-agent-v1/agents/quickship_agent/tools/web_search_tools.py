"""
Web search tool for QuickShip Logistics Agent.
Allowed topics: shipping, logistics, customs, delivery, courier info.
"""
import logging
from langchain.tools import tool
from agents.shared.web_search_base import execute_web_search

logger = logging.getLogger(__name__)

_ALLOWED_KEYWORDS = [
    "shipping", "shipment", "dispatch", "courier", "parcel", "package", "freight",
    "logistics", "warehouse", "fulfillment", "3pl", "last mile", "route", "fleet",
    "customs", "import", "export", "duty", "tariff", "clearance", "border",
    "delivery", "deliver", "transit", "eta", "estimated arrival",
    "track", "tracking", "status", "location",
    "dhl", "fedex", "ups", "bluedart", "delhivery", "ecom express",
    "pin code", "pincode", "serviceable", "cod", "cash on delivery",
    "return pickup", "reverse logistics",
]


def _is_allowed(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in _ALLOWED_KEYWORDS)


def create_web_search_tool():
    @tool
    def web_search(query: str) -> str:
        """
        Search the web for shipping rates, courier information, logistics news,
        customs regulations, or delivery-related queries not in the database.
        """
        if not _is_allowed(query):
            logger.warning(f"QuickShip agent web search blocked (off-topic): {query[:80]}")
            return (
                "I can only search for shipping, logistics, customs, or delivery-related topics. "
                "Please refine your query."
            )
        return execute_web_search(query)

    return web_search
