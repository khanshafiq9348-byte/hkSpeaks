import os
import mimetypes
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from app.services.storage import storage_service

router = APIRouter(prefix="/storage", tags=["Storage"])

@router.api_route("/{file_path:path}", methods=["GET", "HEAD", "OPTIONS"])
async def get_storage_file(file_path: str, request: Request):
    """
    Serves stored media files (audio, video, images) locally with HTTP Range header and HEAD request support.
    Compatible with HTML5 <audio>, <video>, and <img> players/viewers.
    """
    if request.method == "OPTIONS":
        return Response(
            status_code=status.HTTP_200_OK,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )

    local_path = storage_service.get_local_path(file_path)
    if not local_path or not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="Media file not found.")

    file_size = os.path.getsize(local_path)
    filename = os.path.basename(local_path)
    guessed_type, _ = mimetypes.guess_type(local_path)
    content_type = guessed_type or ("video/mp4" if file_path.endswith(".mp4") else "application/octet-stream")

    is_download = request.query_params.get("download") in ("1", "true", "attachment") or "/renders/" in file_path or file_path.endswith(".mp4")

    base_headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": content_type,
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Expose-Headers": "Content-Range, Accept-Ranges, Content-Length, Content-Disposition",
        "Cache-Control": "public, max-age=86400",
    }
    if is_download:
        base_headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    # Handle HEAD request
    if request.method == "HEAD":
        return Response(
            status_code=status.HTTP_200_OK,
            headers={
                **base_headers,
                "Content-Length": str(file_size),
            }
        )

    # Handle Range header (e.g. bytes=0-1024 or bytes=0-)
    range_header = request.headers.get("range")
    if range_header and range_header.startswith("bytes="):
        try:
            byte_range = range_header.replace("bytes=", "").split("-")
            start = int(byte_range[0]) if byte_range[0] else 0
            end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1
            if end >= file_size:
                end = file_size - 1
            chunk_length = (end - start) + 1

            with open(local_path, "rb") as f:
                f.seek(start)
                data = f.read(chunk_length)

            range_headers = {
                **base_headers,
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(chunk_length),
            }
            return Response(data, status_code=status.HTTP_206_PARTIAL_CONTENT, headers=range_headers)
        except Exception:
            pass

    return FileResponse(
        local_path,
        media_type=content_type,
        headers={
            **base_headers,
            "Content-Length": str(file_size),
        }
    )
