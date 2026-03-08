"""Export API routes — export research answers as Markdown or plain text."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/export", tags=["export"])


class ExportRequest(BaseModel):
    title: str
    content: str
    sources: list[dict] = []
    format: str = "markdown"  # "markdown" or "text"


class ExportResponse(BaseModel):
    filename: str
    content: str
    mime_type: str


@router.post("/", response_model=ExportResponse)
async def export_answer(request: ExportRequest):
    """Export a research answer as Markdown or plain text."""
    if request.format == "markdown":
        lines = [f"# {request.title}\n"]
        lines.append(request.content)
        if request.sources:
            lines.append("\n\n---\n\n## Sources\n")
            for i, src in enumerate(request.sources, 1):
                title = src.get("title", "Untitled")
                url = src.get("url", "")
                lines.append(f"{i}. [{title}]({url})")
        return ExportResponse(
            filename=f"{_slugify(request.title)}.md",
            content="\n".join(lines),
            mime_type="text/markdown",
        )
    elif request.format == "text":
        lines = [request.title, "=" * len(request.title), "", request.content]
        if request.sources:
            lines.extend(["", "", "Sources:", "-" * 8])
            for i, src in enumerate(request.sources, 1):
                lines.append(f"{i}. {src.get('title', 'Untitled')} — {src.get('url', '')}")
        return ExportResponse(
            filename=f"{_slugify(request.title)}.txt",
            content="\n".join(lines),
            mime_type="text/plain",
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")


def _slugify(text: str) -> str:
    """Simple slug from title for filename."""
    import re
    slug = re.sub(r'[^\w\s-]', '', text.lower().strip())
    return re.sub(r'[\s_]+', '-', slug)[:60] or "export"
