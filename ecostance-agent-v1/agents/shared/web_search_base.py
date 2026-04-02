"""
Shared web search execution logic.
Tavily (primary) → DuckDuckGo (fallback on quota/rate limit).
"""
import logging
import os

logger = logging.getLogger(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def _tavily_search(query: str) -> str:
    from langchain_community.tools.tavily_search import TavilySearchResults
    results = TavilySearchResults(max_results=3, tavily_api_key=TAVILY_API_KEY).invoke(query)
    if isinstance(results, list):
        return "\n\n".join(
            f"{r.get('title', '')}\n{r.get('content', '')}\nSource: {r.get('url', '')}"
            for r in results
        )
    return str(results)


def _ddg_search(query: str) -> str:
    from langchain_community.tools import DuckDuckGoSearchRun
    return DuckDuckGoSearchRun().invoke(query)


def execute_web_search(query: str) -> str:
    """Run search via Tavily, fall back to DuckDuckGo on quota/rate errors."""
    if TAVILY_API_KEY:
        try:
            result = _tavily_search(query)
            logger.info(f"Web search via Tavily: {query[:60]}")
            return result
        except Exception as e:
            if any(x in str(e).lower() for x in ["quota", "rate", "limit", "429", "402"]):
                logger.warning("Tavily quota exhausted, falling back to DuckDuckGo")
            else:
                logger.warning(f"Tavily failed ({e}), falling back to DuckDuckGo")

    try:
        result = _ddg_search(query)
        logger.info(f"Web search via DuckDuckGo: {query[:60]}")
        return result
    except Exception as e:
        logger.error(f"DuckDuckGo also failed: {e}")
        return f"Web search unavailable. Error: {str(e)}"
