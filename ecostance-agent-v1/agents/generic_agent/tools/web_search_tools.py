"""
Web search tool for Generic Agent.
Allowed topics: business, technology, industry, general knowledge.
"""
import logging
from langchain.tools import tool
from agents.shared.web_search_base import execute_web_search

logger = logging.getLogger(__name__)

_ALLOWED_KEYWORDS = [
    "company", "business", "corporate", "industry", "market", "revenue",
    "startup", "enterprise", "software", "hardware", "tech", "ai", "api",
    "cloud", "developer", "sector", "manufacturing", "supply chain",
    "founded", "ceo", "headquarters", "acquisition", "merger",
    "report", "analysis", "research", "statistics", "data",
]


def _is_allowed(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in _ALLOWED_KEYWORDS)


def create_web_search_tool():
    @tool
    def web_search(query: str) -> str:
        """
        Search the web for business, technology, or industry information
        not available in the database or knowledge base.
        """
        if not _is_allowed(query):
            logger.warning(f"Generic agent web search blocked (off-topic): {query[:80]}")
            return (
                "I can only search for business, technology, or industry-related topics. "
                "Please refine your query."
            )
        return execute_web_search(query)

    return web_search
