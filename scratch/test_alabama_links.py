import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from app.services.content_cleaner import classify_links, is_allowed_domain

async def inspect_alabama_links():
    url = "https://www.alabamapublichealth.gov/about/regulations.html"
    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=30000)
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=config)
        print(f"Success: {result.success}")
        if result.links:
            internal_links = [link.get("href") for link in result.links.get("internal", [])]
            external_links = [link.get("href") for link in result.links.get("external", [])]
            print(f"Total Internal Links: {len(internal_links)}")
            print(f"Total External Links: {len(external_links)}")
            
            all_links = internal_links + external_links
            admincode_links = [l for l in all_links if "admincode" in str(l) or "legislature" in str(l)]
            print(f"\nDiscovered Admincode/Legislature Links ({len(admincode_links)}):")
            for l in admincode_links[:10]:
                print(f"  - {l}")
                
            allowed_domains = ["alabamapublichealth.gov", "legislature.state.al.us", "state.al.us", "adph.org"]
            html_links, pdf_links = classify_links(all_links, url, allowed_domains)
            print(f"\nClassified HTML Links count: {len(html_links)}")
            print(f"Classified PDF Links count: {len(pdf_links)}")
            
            admin_classified = [l for l in html_links if "admincode" in l or "legislature" in l]
            print(f"Classified Admincode Links: {admin_classified}")

if __name__ == "__main__":
    asyncio.run(inspect_alabama_links())
