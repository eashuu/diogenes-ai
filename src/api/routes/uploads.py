"""
File Upload API Routes.

Endpoints for uploading files, querying uploaded content,
and managing uploaded documents for RAG.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from src.services.upload import UploadService
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/uploads", tags=["uploads"])

# Shared singleton
_upload_service: UploadService | None = None


def _get_upload_service() -> UploadService:
    global _upload_service
    if _upload_service is None:
        _upload_service = UploadService()
    return _upload_service


# =============================================================================
# SCHEMAS
# =============================================================================


class UploadResponse(BaseModel):
    files: list[dict]


class QueryRequest(BaseModel):
    queries: list[str] = Field(..., min_length=1, max_length=5)
    file_ids: list[str] = Field(default_factory=list)
    top_k: int = Field(default=10, ge=1, le=50)


class QueryResponse(BaseModel):
    results: list[dict]


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.post("", response_model=UploadResponse)
async def upload_files(files: list[UploadFile] = File(...)):
    """
    Upload one or more files for RAG processing.

    Supported types: PDF, DOCX, TXT, MD, CSV.
    Max size: 20 MB per file.
    """
    service = _get_upload_service()
    uploaded = []

    for f in files:
        try:
            content = await f.read()
            mime = f.content_type or "application/octet-stream"
            result = await service.process_upload(
                filename=f.filename or "unknown",
                content=content,
                mime_type=mime,
            )
            uploaded.append(result.to_dict())
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            logger.exception(f"Upload failed for {f.filename}: {e}")
            raise HTTPException(500, f"Upload processing failed: {e}")

    return UploadResponse(files=uploaded)


@router.post("/query", response_model=QueryResponse)
async def query_uploads(req: QueryRequest):
    """
    Semantic search over uploaded files.

    Returns relevant chunks from previously uploaded documents.
    """
    service = _get_upload_service()
    results = await service.query(
        queries=req.queries,
        file_ids=req.file_ids,
        top_k=req.top_k,
    )
    return QueryResponse(results=results)


@router.get("", response_model=list[dict])
async def list_uploads():
    """List all uploaded files."""
    service = _get_upload_service()
    return await service.list_files()


@router.delete("/{file_id}")
async def delete_upload(file_id: str):
    """Delete an uploaded file and its embeddings."""
    service = _get_upload_service()
    await service.delete_file(file_id)
    return {"status": "ok", "fileId": file_id}
