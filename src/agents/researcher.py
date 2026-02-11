import asyncio
import json
from typing import List, Dict, Any
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.tools.search_tool import SearchTool
from src.tools.crawl_tool import CrawlTool

class Researcher:
    def __init__(self, main_model: str = "gpt-oss:20b-cloud", decomposition_model: str = "qwen3:0.6b"):
        self.search_tool = SearchTool()
        self.crawl_tool = CrawlTool()
        self.main_llm = ChatOllama(model=main_model, temperature=0, base_url="http://localhost:11434")
        self.decomp_llm = ChatOllama(model=decomposition_model, temperature=0, base_url="http://localhost:11434")

    async def decompose_query(self, user_query: str) -> List[str]:
        """
        Decomposes the user query into search-friendly sub-queries.
        """
        print(f"DEBUG: Decomposing query: {user_query}")
        
        prompt = ChatPromptTemplate.from_template(
            """You are an expert research assistant. breakdown the user's complex query into 2-4 distinct, specific search queries that will help gather comprehensive information.
            
            User Query: {query}
            
            Return ONLY the queries, one per line. Do not number them.
            """
        )
        
        chain = prompt | self.decomp_llm | StrOutputParser()
        response = await chain.ainvoke({"query": user_query})
        
        # Clean response lines
        queries = []
        for q in response.split('\n'):
            q = q.strip()
            if not q:
                continue
            # Remove leading bullets, numbers, dashes
            cleaned = q.lstrip('-*•0123456789. ')
            if cleaned:
                queries.append(cleaned)
        
        # Always include original query at the top
        if user_query not in queries:
            queries.insert(0, user_query)
        
        return queries[:5] # Limit just in case

    async def execute_research(self, user_query: str, max_urls_to_crawl: int = 5) -> Dict[str, Any]:
        """
        Main entry point: Decompose -> Search -> Aggregate -> Crawl
        """
        # 1. Decompose
        sub_queries = await self.decompose_query(user_query)
        print(f"DEBUG: Generated sub-queries: {sub_queries}")
        
        # 2. Search (Parallel)
        all_results = []
        # We could run these async but SearchTool is sync for now (httpx sync client), 
        # so we run them sequentially or wrap in threadpool. 
        # For simplicity, sequential is fine for 3-4 queries or we can map it.
        for q in sub_queries:
            results = self.search_tool.search(q, num_results=5)
            all_results.extend(results)
            
        # 3. Aggregate & Deduplicate
        unique_results = {}
        for r in all_results:
            if r['url'] not in unique_results:
                unique_results[r['url']] = r
            else:
                # Merge scores or boost?
                pass
                
        # List of unique items sorted by score (if available) - SearchTool mocks score for now essentially
        sorted_results = list(unique_results.values())
        # If SearXNG gives score, sort by it. Otherwise just trust the order (top hits).
        # We'll take the top N items.
        top_urls_to_crawl = [r['url'] for r in sorted_results[:max_urls_to_crawl]]
        
        print(f"DEBUG: Selected {len(top_urls_to_crawl)} URLs to crawl.")
        
        # 4. Crawl
        crawled_data = await self.crawl_tool.crawl_urls(top_urls_to_crawl)
        
        return {
            "original_query": user_query,
            "sub_queries": sub_queries,
            "search_results_count": len(sorted_results),
            "crawled_data": crawled_data
        }

    async def synthesize_research(self, data: Dict[str, Any]) -> str:
        """
        Synthesizes the crawled data into a coherent answer.
        """
        print("DEBUG: Synthesizing answer using main LLM...")
        
        # Prepare context (simple truncation for now)
        context_parts = []
        total_chars = 0
        limit = 32000 # Conservative limit for context window
        
        for item in data.get('crawled_data', []):
            title = item.get('title', 'Unknown Source')
            url = item.get('url', '')
            content = item.get('markdown', '')
            
            # Skip empty content
            if not content:
                continue
                
            # Add header
            part = f"\n--- Source: {title} ({url}) ---\n"
            context_parts.append(part)
            total_chars += len(part)
            
            # Add content (truncated per source to ensure variety)
            # giving each of 5 sources roughly 6000 chars
            content_limit = 6000
            truncated_content = content[:content_limit]
            context_parts.append(truncated_content)
            total_chars += len(truncated_content)
            
            if total_chars >= limit:
                break
                
        full_context = "".join(context_parts)
        
        prompt = ChatPromptTemplate.from_template(
            """You are Diogenes, a private AI research assistant. 
            Based ONLY on the provided context, answer the user's research query.
            
            User Query: {query}
            
            Context:
            {context}
            
            Instructions:
            1. synthesize a comprehensive answer.
            2. Cite your sources using [Source Name] or [URL] format when possible.
            3. If the context doesn't contain the answer, state that clearly.
            4. Be professional, detailed, and objective.
            """
        )
        
        chain = prompt | self.main_llm | StrOutputParser()
        return await chain.ainvoke({"query": data['original_query'], "context": full_context})

if __name__ == "__main__":
    async def main():
        researcher = Researcher()
        final_data = await researcher.execute_research("What is the current state of solid state batteries in 2025?")
        
        print("\n--- Research Summary ---")
        print(f"Sub-queries: {final_data['sub_queries']}")
        print(f"Crawled {len(final_data['crawled_data'])} pages.")
        for page in final_data['crawled_data']:
            print(f" - {page['title']} ({len(page.get('markdown', ''))} chars)")

    asyncio.run(main())
