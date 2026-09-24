import io
import httpx
from typing import Dict, Any
from pypdf import PdfReader
from app.services.content_cleaner import calculate_sha256
from app.utils.logger import logger


async def download_and_extract_pdf(url: str, timeout: int = 30) -> Dict[str, Any]:
    """Asynchronously downloads a PDF document and extracts plain text pages."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch PDF at {url}. Status code: {resp.status_code}")
                return {
                    "url": url,
                    "type": "pdf",
                    "success": False,
                    "error": f"HTTP status {resp.status_code}",
                    "text": None,
                    "content_hash": None,
                    "page_count": 0
                }

            pdf_file = io.BytesIO(resp.content)
            reader = PdfReader(pdf_file)
            extracted_pages = []

            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    extracted_pages.append(f"### Page {i+1}\n\n{page_text.strip()}")

            full_markdown = f"# PDF Document: {url}\n\n" + "\n\n---\n\n".join(extracted_pages)
            
            return {
                "url": url,
                "type": "pdf",
                "success": True,
                "error": None,
                "text": full_markdown,
                "content_hash": calculate_sha256(full_markdown),
                "page_count": len(reader.pages)
            }
    except Exception as e:
        logger.error(f"Error processing PDF at {url}: {str(e)}")
        return {
            "url": url,
            "type": "pdf",
            "success": False,
            "error": str(e),
            "text": None,
            "content_hash": None,
            "page_count": 0
        }