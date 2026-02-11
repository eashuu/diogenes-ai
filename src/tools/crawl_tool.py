import asyncio
from typing import List, Dict, Any
from crawl4ai import AsyncWebCrawler

class CrawlTool:
    def __init__(self):
        pass

    async def crawl_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Crawls a list of URLs in parallel and returns the markdown content.
        """
        results = []
        print(f"DEBUG: Starting crawl for {len(urls)} URLs...")
        
        async with AsyncWebCrawler(verbose=True) as crawler:
            # Create tasks for all URLs
            tasks = [crawler.arun(url=url) for url in urls]
            crawl_results = await asyncio.gather(*tasks)
            
            for i, result in enumerate(crawl_results):
                if result.success:
                    results.append({
                        "url": urls[i],
                        "title": result.metadata.get("title", "No Title"),
                        "markdown": result.markdown,
                        "status": "success"
                    })
                else:
                    results.append({
                        "url": urls[i],
                        "status": "error",
                        "error_message": result.error_message
                    })
                    
        return results

if __name__ == "__main__":
    # Test
    async def main():
        tool = CrawlTool()
        res = await tool.crawl_urls(["https://example.com"])
        print(res[0]['markdown'][:100])

    asyncio.run(main())
