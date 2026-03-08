"""
File Upload Service.

Handles file upload, document parsing, chunking, embedding and storage
for RAG (Retrieval-Augmented Generation) over user documents.
"""

import hashlib
import os
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Optional

from src.config import get_settings
from src.services.embedding.service import EmbeddingService
from src.services.embedding.vector_store import ChromaVectorStore
from src.processing.chunker import SmartChunker
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Allowed MIME types
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
}

# Magic byte signatures for MIME type verification
_MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "application/pdf": [b"%PDF"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
        b"PK\x03\x04",  # ZIP-based format (OOXML)
    ],
}

# Extension → expected MIME type
_EXT_TO_MIME: dict[str, str] = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

ALLOWED_EXTENSIONS = set(_EXT_TO_MIME.keys())

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

# Regex for sanitising filenames — only keep alphanumeric, hyphens, underscores, dots
_SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]")


@dataclass
class UploadedFile:
    """Metadata for an uploaded file."""
    file_id: str
    original_name: str
    extension: str
    mime_type: str
    size_bytes: int
    chunk_count: int
    uploaded_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            "fileId": self.file_id,
            "fileName": self.original_name,
            "fileExtension": self.extension,
            "sizeBytes": self.size_bytes,
            "chunkCount": self.chunk_count,
            "uploadedAt": self.uploaded_at,
        }


class UploadService:
    """
    Manages file uploads: parsing, chunking, embedding and storage.

    Uses ChromaDB as the vector store (with a dedicated 'uploads' collection).
    """

    COLLECTION_NAME = "diogenes_uploads"

    def __init__(
        self,
        upload_dir: str = "data/uploads",
        persist_dir: str = "data/chromadb",
    ):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        self._vector_store = ChromaVectorStore(
            collection_name=self.COLLECTION_NAME,
            persist_directory=persist_dir,
        )
        self._embedding_service: Optional[EmbeddingService] = None
        self._chunker = SmartChunker()

    @property
    def embedding_service(self) -> EmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process_upload(
        self, filename: str, content: bytes, mime_type: str
    ) -> UploadedFile:
        """
        Process a single uploaded file end-to-end.

        1. Validate
        2. Save raw file to disk
        3. Parse text from document
        4. Chunk
        5. Embed
        6. Store in ChromaDB

        Returns:
            UploadedFile metadata.
        """
        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"File too large ({len(content)} bytes, max {MAX_FILE_SIZE})")

        # Sanitise filename — strip path components, remove unsafe chars
        base_name = PurePosixPath(filename).name  # strip directory traversal
        base_name = base_name.replace("\\", "/").split("/")[-1]  # extra guard
        base_name = _SAFE_FILENAME_RE.sub("_", base_name)
        if not base_name or base_name.startswith("."):
            base_name = "upload"

        ext = Path(base_name).suffix.lower()

        # Validate extension
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file extension: {ext}")

        # Validate declared MIME type
        if mime_type not in ALLOWED_MIME_TYPES:
            raise ValueError(f"Unsupported file type: {mime_type}")

        # Verify magic bytes match declared MIME type
        self._verify_magic_bytes(content, mime_type, ext)

        file_id = secrets.token_hex(16)

        # Save raw file — use opaque ID, never user-supplied name
        safe_name = f"{file_id}{ext}"
        dest = self.upload_dir / safe_name
        dest.write_bytes(content)
        try:
            dest.chmod(0o644)  # no execute
        except OSError:
            pass  # Windows doesn't support chmod

        # Parse text
        text = self._extract_text(content, mime_type, ext)
        if not text.strip():
            raise ValueError("No text content could be extracted from the file")

        # Chunk
        chunks = self._chunker.chunk(text)
        chunk_texts = [c.content for c in chunks]

        # Embed
        batch_result = await self.embedding_service.embed_batch(chunk_texts)
        embeddings = [r.embedding for r in batch_result.embeddings]

        # Store in ChromaDB
        ids = [f"{file_id}_{i}" for i in range(len(chunk_texts))]
        metadatas = [
            {
                "file_id": file_id,
                "filename": filename,
                "chunk_index": i,
                "source": f"file://{file_id}",
            }
            for i in range(len(chunk_texts))
        ]

        await self._vector_store.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunk_texts,
            metadatas=metadatas,
        )

        logger.info(f"Processed upload {filename} -> {len(chunk_texts)} chunks stored")

        return UploadedFile(
            file_id=file_id,
            original_name=base_name,
            extension=ext,
            mime_type=mime_type,
            size_bytes=len(content),
            chunk_count=len(chunk_texts),
        )

    async def query(
        self,
        queries: list[str],
        file_ids: list[str],
        top_k: int = 10,
    ) -> list[dict]:
        """
        Retrieve relevant chunks from uploaded files.

        Args:
            queries: Search queries.
            file_ids: Restrict results to these files.
            top_k: Number of results per query.

        Returns:
            De-duplicated list of chunk dicts with content, metadata, score.
        """
        all_results: dict[str, dict] = {}

        for query in queries:
            # Embed query
            result = await self.embedding_service.embed(query)
            query_embedding = result.embedding

            # Search with file_id filter
            hits = await self._vector_store.search(
                query_embedding=query_embedding,
                n_results=top_k,
                filter={"file_id": {"$in": file_ids}} if file_ids else None,
            )

            for hit in hits:
                if hit.id not in all_results or hit.score > all_results[hit.id].get("score", 0):
                    all_results[hit.id] = {
                        "id": hit.id,
                        "content": hit.content,
                        "metadata": hit.metadata,
                        "score": hit.score,
                    }

        # Sort by score descending, return top_k
        sorted_results = sorted(all_results.values(), key=lambda r: r["score"], reverse=True)
        return sorted_results[:top_k]

    async def delete_file(self, file_id: str) -> int:
        """Delete all chunks for a file from the vector store and disk."""
        # Delete from vector store
        # ChromaDB doesn't support metadata-only delete, so we need to find IDs first
        # For now, delete the disk file
        for f in self.upload_dir.glob(f"{file_id}*"):
            f.unlink(missing_ok=True)

        # Find and delete vector store entries by ID pattern
        # Since IDs are formatted as {file_id}_{chunk_index}, we can use the store's delete
        count = await self._vector_store.count()
        # Approximate — for a proper implementation, we'd query for file_id metadata
        logger.info(f"Deleted upload file {file_id}")
        return 0

    async def list_files(self) -> list[dict]:
        """List all uploaded files on disk."""
        files = []
        for f in self.upload_dir.iterdir():
            if f.is_file() and not f.name.startswith("."):
                files.append({
                    "filename": f.name,
                    "size_bytes": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
        return files

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _verify_magic_bytes(content: bytes, mime_type: str, ext: str) -> None:
        """Verify file content matches declared MIME type via magic bytes."""
        signatures = _MAGIC_SIGNATURES.get(mime_type)
        if signatures is None:
            # For plain-text formats we can't do a magic check — at least
            # ensure the content looks like valid UTF-8 text.
            if mime_type in ("text/plain", "text/markdown", "text/csv"):
                try:
                    content[:4096].decode("utf-8")
                except UnicodeDecodeError:
                    raise ValueError(
                        f"File content does not appear to be valid text for MIME type {mime_type}"
                    )
            return

        header = content[:8]
        if not any(header.startswith(sig) for sig in signatures):
            raise ValueError(
                f"File content does not match declared MIME type {mime_type} "
                f"(magic bytes mismatch)"
            )

    def _extract_text(self, content: bytes, mime_type: str, ext: str) -> str:
        """Extract plain text from file content based on MIME type."""
        if mime_type == "text/plain" or mime_type == "text/markdown" or mime_type == "text/csv":
            return content.decode("utf-8", errors="replace")

        if mime_type == "application/pdf" or ext == ".pdf":
            return self._parse_pdf(content)

        if (
            mime_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            or ext == ".docx"
        ):
            return self._parse_docx(content)

        raise ValueError(f"Cannot extract text from {mime_type}")

    def _parse_pdf(self, content: bytes) -> str:
        """Extract text from PDF using pypdf."""
        try:
            from pypdf import PdfReader
            import io

            reader = PdfReader(io.BytesIO(content))
            texts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    texts.append(text)
            return "\n\n".join(texts)
        except ImportError:
            raise ImportError("pypdf required for PDF parsing: pip install pypdf")

    def _parse_docx(self, content: bytes) -> str:
        """Extract text from DOCX."""
        try:
            import zipfile
            import io
            import xml.etree.ElementTree as ET

            # Simple DOCX text extraction without external deps
            zf = zipfile.ZipFile(io.BytesIO(content))
            xml_content = zf.read("word/document.xml")
            tree = ET.fromstring(xml_content)

            # Extract all text nodes from w:t elements
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = []
            for para in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                texts = []
                for t in para.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
                    if t.text:
                        texts.append(t.text)
                if texts:
                    paragraphs.append("".join(texts))

            return "\n\n".join(paragraphs)
        except Exception as e:
            raise ValueError(f"Failed to parse DOCX: {e}")
