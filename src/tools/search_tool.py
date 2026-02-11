import httpx
from typing import List, Dict, Any
import json

class SearchTool:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.headers = {
            "User-Agent": "DiogenesResearchAgent/1.0"
        }

    def search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Executes a search query against SearXNG and returns valid results.
        """
        params = {
            "q": query,
            "format": "json",
            "categories": "general,science,it",  # Focused categories
            "language": "en-US"
        }
        
        try:
            print(f"DEBUG: Searching SearXNG for: '{query}'")
            with httpx.Client(timeout=20.0) as client:
                response = client.get(f"{self.base_url}/search", params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
            results = data.get("results", [])
            
            # Basic filtering and cleaning
            cleaned_results = []
            seen_urls = set()
            
            for res in results:
                url = res.get("url")
                if url in seen_urls:
                    continue
                
                # Skip youtube and other non-text heavy sites if desired
                # if "youtube.com" in url: continue

                cleaned_results.append({
                    "title": res.get("title"),
                    "url": url,
                    "content": res.get("content", ""),
                    "score": res.get("score", 0)
                })
                seen_urls.add(url)
                
                if len(cleaned_results) >= num_results:
                    break
                    
            return cleaned_results

        except Exception as e:
            print(f"Error querying SearXNG: {e}")
            return []

if __name__ == "__main__":
    # Simple test
    tool = SearchTool()
    results = tool.search("latest open source AI models")
    print(json.dumps(results[:2], indent=2))
