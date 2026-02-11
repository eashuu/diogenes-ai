"""
Legacy tool wrappers — DEPRECATED.

These modules (``search_tool`` and ``crawl_tool``) are thin wrappers around
SearXNG and Crawl4AI that were used by the old LangGraph-based CLI agent
in ``src/agents/researcher.py``.

**Do not use these in new code.**  Use the service layer directly:

- ``src.services.search.searxng.SearXNGService``
- ``src.services.crawl.crawler.Crawl4AIService``
"""
