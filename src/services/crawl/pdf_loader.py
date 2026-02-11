"""
PDF Document Loader.

Extracts text and metadata from PDF documents for research ingestion.
"""

import io
import re
from typing import Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

import httpx

from src.utils.logging import get_logger


logger = get_logger(__name__)


@dataclass
class PDFMetadata:
    """Metadata extracted from PDF."""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    page_count: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "author": self.author,
            "subject": self.subject,
            "creator": self.creator,
            "producer": self.producer,
            "creation_date": self.creation_date.isoformat() if self.creation_date else None,
            "modification_date": self.modification_date.isoformat() if self.modification_date else None,
            "page_count": self.page_count
        }


@dataclass
class PDFPage:
    """A single page from a PDF."""
    page_number: int  # 1-indexed
    text: str
    char_count: int
    word_count: int


@dataclass
class PDFDocument:
    """Extracted PDF document."""
    source: str  # URL or file path
    metadata: PDFMetadata
    pages: list[PDFPage]
    full_text: str
    extraction_method: str
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def total_words(self) -> int:
        """Total word count."""
        return sum(p.word_count for p in self.pages)
    
    @property
    def total_chars(self) -> int:
        """Total character count."""
        return sum(p.char_count for p in self.pages)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "metadata": self.metadata.to_dict(),
            "page_count": len(self.pages),
            "total_words": self.total_words,
            "total_chars": self.total_chars,
            "extraction_method": self.extraction_method,
            "extracted_at": self.extracted_at.isoformat()
        }


class PDFLoader:
    """
    PDF document loader and text extractor.
    
    Supports:
    - Loading from file path
    - Loading from URL (e.g., arXiv PDFs)
    - Text extraction with multiple backends
    - Metadata extraction
    - Page-by-page text
    
    Usage:
        loader = PDFLoader()
        
        # From file
        doc = await loader.load_file("paper.pdf")
        
        # From URL
        doc = await loader.load_url("https://arxiv.org/pdf/2103.14030.pdf")
        
        print(doc.full_text)
        print(doc.metadata.title)
    
    Backends:
    - pypdf: Pure Python, reliable (default)
    - pdfplumber: Better for tables
    - pdfminer: More accurate text extraction
    """
    
    def __init__(
        self,
        backend: str = "pypdf",
        timeout: float = 60.0,
        max_pages: int = 500
    ):
        """
        Initialize PDF loader.
        
        Args:
            backend: Extraction backend ("pypdf", "pdfplumber", "pdfminer")
            timeout: HTTP timeout for URL downloads
            max_pages: Maximum pages to extract
        """
        self.backend = backend
        self.timeout = timeout
        self.max_pages = max_pages
        self._client: Optional[httpx.AsyncClient] = None
        
        # Check backend availability
        self._check_backend()
    
    def _check_backend(self):
        """Check if the selected backend is available."""
        if self.backend == "pypdf":
            try:
                import pypdf
                self._pypdf = pypdf
            except ImportError:
                raise ImportError("pypdf required. Install with: pip install pypdf")
                
        elif self.backend == "pdfplumber":
            try:
                import pdfplumber
                self._pdfplumber = pdfplumber
            except ImportError:
                raise ImportError("pdfplumber required. Install with: pip install pdfplumber")
                
        elif self.backend == "pdfminer":
            try:
                from pdfminer.high_level import extract_text, extract_pages
                from pdfminer.pdfparser import PDFParser
                from pdfminer.pdfdocument import PDFDocument as PMDocument
                self._pdfminer_extract_text = extract_text
                self._pdfminer_extract_pages = extract_pages
            except ImportError:
                raise ImportError("pdfminer.six required. Install with: pip install pdfminer.six")
        else:
            raise ValueError(f"Unknown backend: {self.backend}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Diogenes/2.0 (research assistant)",
                    "Accept": "application/pdf"
                }
            )
        return self._client
    
    async def load_url(self, url: str) -> PDFDocument:
        """
        Load and extract PDF from URL.
        
        Args:
            url: URL to PDF file
            
        Returns:
            PDFDocument with extracted content
        """
        logger.info(f"Downloading PDF from: {url}")
        
        client = await self._get_client()
        response = await client.get(url)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
            logger.warning(f"Content type is {content_type}, may not be PDF")
        
        pdf_bytes = response.content
        logger.info(f"Downloaded {len(pdf_bytes)} bytes")
        
        return self._extract(pdf_bytes, source=url)
    
    async def load_file(self, path: str) -> PDFDocument:
        """
        Load and extract PDF from file.
        
        Args:
            path: Path to PDF file
            
        Returns:
            PDFDocument with extracted content
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        
        logger.info(f"Loading PDF from: {path}")
        
        pdf_bytes = file_path.read_bytes()
        
        return self._extract(pdf_bytes, source=str(file_path.absolute()))
    
    def _extract(self, pdf_bytes: bytes, source: str) -> PDFDocument:
        """Extract text and metadata from PDF bytes."""
        if self.backend == "pypdf":
            return self._extract_pypdf(pdf_bytes, source)
        elif self.backend == "pdfplumber":
            return self._extract_pdfplumber(pdf_bytes, source)
        elif self.backend == "pdfminer":
            return self._extract_pdfminer(pdf_bytes, source)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")
    
    def _extract_pypdf(self, pdf_bytes: bytes, source: str) -> PDFDocument:
        """Extract using pypdf."""
        reader = self._pypdf.PdfReader(io.BytesIO(pdf_bytes))
        
        # Extract metadata
        info = reader.metadata or {}
        metadata = PDFMetadata(
            title=str(info.get("/Title", "")) or None,
            author=str(info.get("/Author", "")) or None,
            subject=str(info.get("/Subject", "")) or None,
            creator=str(info.get("/Creator", "")) or None,
            producer=str(info.get("/Producer", "")) or None,
            page_count=len(reader.pages)
        )
        
        # Try to parse dates
        if "/CreationDate" in info:
            metadata.creation_date = self._parse_pdf_date(str(info["/CreationDate"]))
        if "/ModDate" in info:
            metadata.modification_date = self._parse_pdf_date(str(info["/ModDate"]))
        
        # Extract pages
        pages = []
        full_text_parts = []
        
        for i, page in enumerate(reader.pages):
            if i >= self.max_pages:
                logger.warning(f"Stopping at {self.max_pages} pages")
                break
            
            try:
                text = page.extract_text() or ""
                text = self._clean_text(text)
                
                pages.append(PDFPage(
                    page_number=i + 1,
                    text=text,
                    char_count=len(text),
                    word_count=len(text.split())
                ))
                full_text_parts.append(text)
                
            except Exception as e:
                logger.warning(f"Failed to extract page {i + 1}: {e}")
                continue
        
        full_text = "\n\n".join(full_text_parts)
        
        logger.info(f"Extracted {len(pages)} pages, {len(full_text)} chars")
        
        return PDFDocument(
            source=source,
            metadata=metadata,
            pages=pages,
            full_text=full_text,
            extraction_method=f"pypdf-{self._pypdf.__version__}"
        )
    
    def _extract_pdfplumber(self, pdf_bytes: bytes, source: str) -> PDFDocument:
        """Extract using pdfplumber."""
        with self._pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            # Extract metadata
            info = pdf.metadata or {}
            metadata = PDFMetadata(
                title=info.get("Title"),
                author=info.get("Author"),
                subject=info.get("Subject"),
                creator=info.get("Creator"),
                producer=info.get("Producer"),
                page_count=len(pdf.pages)
            )
            
            # Extract pages
            pages = []
            full_text_parts = []
            
            for i, page in enumerate(pdf.pages):
                if i >= self.max_pages:
                    break
                
                try:
                    text = page.extract_text() or ""
                    text = self._clean_text(text)
                    
                    pages.append(PDFPage(
                        page_number=i + 1,
                        text=text,
                        char_count=len(text),
                        word_count=len(text.split())
                    ))
                    full_text_parts.append(text)
                    
                except Exception as e:
                    logger.warning(f"Failed to extract page {i + 1}: {e}")
                    continue
        
        full_text = "\n\n".join(full_text_parts)
        
        return PDFDocument(
            source=source,
            metadata=metadata,
            pages=pages,
            full_text=full_text,
            extraction_method="pdfplumber"
        )
    
    def _extract_pdfminer(self, pdf_bytes: bytes, source: str) -> PDFDocument:
        """Extract using pdfminer."""
        from pdfminer.pdfparser import PDFParser
        from pdfminer.pdfdocument import PDFDocument as PMDocument
        
        pdf_file = io.BytesIO(pdf_bytes)
        
        # Extract metadata
        parser = PDFParser(pdf_file)
        doc = PMDocument(parser)
        info = doc.info[0] if doc.info else {}
        
        metadata = PDFMetadata(
            title=self._decode_pdf_string(info.get("Title")),
            author=self._decode_pdf_string(info.get("Author")),
            subject=self._decode_pdf_string(info.get("Subject")),
            creator=self._decode_pdf_string(info.get("Creator")),
            producer=self._decode_pdf_string(info.get("Producer"))
        )
        
        # Reset for text extraction
        pdf_file.seek(0)
        
        # Extract full text
        full_text = self._pdfminer_extract_text(pdf_file)
        full_text = self._clean_text(full_text)
        
        # PDFMiner doesn't easily give page-by-page, so estimate
        # Split by form feed or double newlines
        page_texts = re.split(r'\f|\n{3,}', full_text)
        pages = []
        for i, text in enumerate(page_texts):
            if i >= self.max_pages:
                break
            text = text.strip()
            if text:
                pages.append(PDFPage(
                    page_number=i + 1,
                    text=text,
                    char_count=len(text),
                    word_count=len(text.split())
                ))
        
        metadata.page_count = len(pages)
        
        return PDFDocument(
            source=source,
            metadata=metadata,
            pages=pages,
            full_text=full_text,
            extraction_method="pdfminer"
        )
    
    def _decode_pdf_string(self, value: Any) -> Optional[str]:
        """Decode PDF string value."""
        if value is None:
            return None
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    return value.decode("latin-1")
                except Exception:
                    return None
        return str(value) if value else None
    
    def _parse_pdf_date(self, date_str: str) -> Optional[datetime]:
        """Parse PDF date format (D:YYYYMMDDHHmmSS)."""
        if not date_str:
            return None
        
        try:
            # Remove D: prefix if present
            if date_str.startswith("D:"):
                date_str = date_str[2:]
            
            # Basic format: YYYYMMDDHHMMSS
            if len(date_str) >= 14:
                return datetime(
                    year=int(date_str[0:4]),
                    month=int(date_str[4:6]),
                    day=int(date_str[6:8]),
                    hour=int(date_str[8:10]),
                    minute=int(date_str[10:12]),
                    second=int(date_str[12:14])
                )
            elif len(date_str) >= 8:
                return datetime(
                    year=int(date_str[0:4]),
                    month=int(date_str[4:6]),
                    day=int(date_str[6:8])
                )
        except Exception:
            pass
        
        return None
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Fix hyphenation at line breaks
        text = re.sub(r'-\s*\n\s*', '', text)
        
        # Normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove control characters except newlines
        text = re.sub(r'[\x00-\x09\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        return text.strip()
    
    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


class PDFChunker:
    """
    Chunk PDF documents for embedding and retrieval.
    
    Strategies:
    - page: One chunk per page
    - paragraph: Split on paragraph boundaries
    - sentence: Split on sentences with overlap
    - fixed: Fixed character count with overlap
    """
    
    def __init__(
        self,
        strategy: str = "paragraph",
        chunk_size: int = 1000,
        overlap: int = 200
    ):
        """
        Initialize chunker.
        
        Args:
            strategy: Chunking strategy
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks
        """
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, document: PDFDocument) -> list[dict[str, Any]]:
        """
        Chunk a PDF document.
        
        Args:
            document: PDF document to chunk
            
        Returns:
            List of chunk dicts with text and metadata
        """
        if self.strategy == "page":
            return self._chunk_by_page(document)
        elif self.strategy == "paragraph":
            return self._chunk_by_paragraph(document)
        elif self.strategy == "sentence":
            return self._chunk_by_sentence(document)
        elif self.strategy == "fixed":
            return self._chunk_fixed(document)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")
    
    def _chunk_by_page(self, document: PDFDocument) -> list[dict[str, Any]]:
        """One chunk per page."""
        chunks = []
        for page in document.pages:
            if page.text.strip():
                chunks.append({
                    "text": page.text,
                    "source": document.source,
                    "page": page.page_number,
                    "chunk_type": "page"
                })
        return chunks
    
    def _chunk_by_paragraph(self, document: PDFDocument) -> list[dict[str, Any]]:
        """Split on paragraph boundaries."""
        chunks = []
        
        # Split on double newlines
        paragraphs = re.split(r'\n\n+', document.full_text)
        
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            if current_size + para_size > self.chunk_size and current_chunk:
                # Emit current chunk
                chunks.append({
                    "text": "\n\n".join(current_chunk),
                    "source": document.source,
                    "chunk_type": "paragraph"
                })
                # Keep last paragraph for overlap
                current_chunk = [current_chunk[-1]] if current_chunk else []
                current_size = len(current_chunk[0]) if current_chunk else 0
            
            current_chunk.append(para)
            current_size += para_size
        
        # Emit remaining
        if current_chunk:
            chunks.append({
                "text": "\n\n".join(current_chunk),
                "source": document.source,
                "chunk_type": "paragraph"
            })
        
        return chunks
    
    def _chunk_by_sentence(self, document: PDFDocument) -> list[dict[str, Any]]:
        """Split on sentence boundaries with overlap."""
        chunks = []
        
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', document.full_text)
        
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sent_size = len(sentence)
            
            if current_size + sent_size > self.chunk_size and current_chunk:
                # Emit current chunk
                chunks.append({
                    "text": " ".join(current_chunk),
                    "source": document.source,
                    "chunk_type": "sentence"
                })
                
                # Keep sentences for overlap
                overlap_size = 0
                overlap_sents = []
                for s in reversed(current_chunk):
                    if overlap_size + len(s) <= self.overlap:
                        overlap_sents.insert(0, s)
                        overlap_size += len(s)
                    else:
                        break
                
                current_chunk = overlap_sents
                current_size = overlap_size
            
            current_chunk.append(sentence)
            current_size += sent_size
        
        # Emit remaining
        if current_chunk:
            chunks.append({
                "text": " ".join(current_chunk),
                "source": document.source,
                "chunk_type": "sentence"
            })
        
        return chunks
    
    def _chunk_fixed(self, document: PDFDocument) -> list[dict[str, Any]]:
        """Fixed size chunks with overlap."""
        chunks = []
        text = document.full_text
        
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]
            
            # Try to break at word boundary
            if end < len(text):
                last_space = chunk_text.rfind(' ')
                if last_space > self.chunk_size // 2:
                    chunk_text = chunk_text[:last_space]
                    end = start + last_space
            
            chunks.append({
                "text": chunk_text.strip(),
                "source": document.source,
                "chunk_type": "fixed",
                "start_char": start,
                "end_char": end
            })
            
            start = end - self.overlap
        
        return chunks
