import re
import httpx
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from app.services.pdf_processor import download_and_extract_pdf
from app.services.content_cleaner import is_pdf_url
from app.utils.logger import logger


class AgentReachReader:
    """
    Agent Reach access & capability layer.
    
    Responsibilities:
    - Open candidate URLs
    - Access webpage or document content safely
    - Extract headings, titles, previews, and body text
    - Format candidate content for Grok relevance evaluation
    
    Non-Responsibilities:
    - NO link crawling or depth traversal
    - NO relevance classification
    - NO legal interpretation
    - NO candidate approval or database persistence
    """

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    async def read_candidate_content(self, url: str, content_type: str = "html") -> Dict[str, Any]:
        """
        Reads candidate webpage or PDF content and returns structured page information.
        Does NOT raise exceptions to caller; returns error status dict on failure.
        """
        if is_pdf_url(url) or content_type == "pdf":
            return await self._read_pdf_candidate(url)
        return await self._read_html_candidate(url)

    async def _read_html_candidate(self, url: str) -> Dict[str, Any]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36 AgentReach/1.0"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    logger.warning(f"Agent Reach HTTP {resp.status_code} for URL: {url}")
                    return {
                        "url": url,
                        "success": False,
                        "error": f"HTTP status {resp.status_code}",
                        "title": None,
                        "headings": [],
                        "content": "",
                        "content_preview": "",
                        "content_type": "html"
                    }

                html_text = resp.text
                title, headings, clean_body = self._extract_html_elements(html_text)
                preview = clean_body[:500] if clean_body else ""

                return {
                    "url": url,
                    "success": True,
                    "error": None,
                    "title": title,
                    "headings": headings,
                    "content": clean_body,
                    "content_preview": preview,
                    "content_type": "html"
                }

        except Exception as e:
            logger.error(f"Agent Reach failed to read HTML candidate {url}: {str(e)}")
            return {
                "url": url,
                "success": False,
                "error": str(e),
                "title": None,
                "headings": [],
                "content": "",
                "content_preview": "",
                "content_type": "html"
            }

    async def _read_pdf_candidate(self, url: str) -> Dict[str, Any]:
        pdf_res = await download_and_extract_pdf(url, timeout=self.timeout)
        if not pdf_res.get("success") or not pdf_res.get("text"):
            return {
                "url": url,
                "success": False,
                "error": pdf_res.get("error", "PDF extraction returned no text"),
                "title": f"PDF Document: {url}",
                "headings": ["PDF Document"],
                "content": "",
                "content_preview": "",
                "content_type": "pdf"
            }

        full_text = pdf_res["text"]
        preview = full_text[:500] if full_text else ""
        headings = re.findall(r"(?m)^#{1,3}\s+(.+)$", full_text)

        return {
            "url": url,
            "success": True,
            "error": None,
            "title": f"PDF Document: {url}",
            "headings": headings,
            "content": full_text,
            "content_preview": preview,
            "content_type": "pdf"
        }

    def _extract_html_elements(self, html: str) -> tuple[Optional[str], list[str], str]:
        """Extracts page title, major headings (h1, h2, h3), and strips HTML tags."""
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else None
        if title:
            title = re.sub(r"\s+", " ", title)

        headings = [
            re.sub(r"\s+", " ", h.strip())
            for h in re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html, re.IGNORECASE | re.DOTALL)
            if h.strip()
        ][:15]

        # Strip scripts, styles, forms, and HTML tags for clean body text
        cleaned_html = re.sub(r"<(script|style|svg|form|nav|footer|header)[^>]*>.*?</\1>", "", html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", cleaned_html)
        text = re.sub(r"&[a-zA-Z0-9#]+;", " ", text)
        clean_body = re.sub(r"\s+", " ", text).strip()

        return title, headings, clean_body
