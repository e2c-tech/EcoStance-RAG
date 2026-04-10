"""
Web search tool for Ecommerce Agent.
Used for general/educational queries only. Product suggestions must always come from shop tools.
"""
import logging
from langchain.tools import tool
from agents.shared.web_search_base import execute_web_search

logger = logging.getLogger(__name__)


def create_web_search_tool():
    @tool
    def web_search(query: str) -> str:
        """
        Search the web for general or educational information only — such as explaining concepts,
        ingredient details, technology comparisons, or background knowledge.
        This tool must NEVER be used to find, list, or suggest products.
        All product suggestions must come exclusively from the shop's own database or API tools.
        """
        return execute_web_search(query)

    return web_search
