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

    is_download = request.query_params.get("download") in ("1", "true", "attachment")
    custom_filename = request.query_params.get("filename") or filename

    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Expose-Headers": "Content-Range, Accept-Ranges, Content-Length, Content-Disposition",
        "Cache-Control": "public, max-age=86400",
    }

    # Handle HEAD request
    if request.method == "HEAD":
        head_headers = {
            **cors_headers,
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": "application/octet-stream" if is_download else content_type,
        }
        if is_download:
            head_headers["Content-Disposition"] = f'attachment; filename="{custom_filename}"'
        else:
            head_headers["Content-Disposition"] = "inline"
        return Response(
            status_code=status.HTTP_200_OK,
            headers=head_headers
        )

    if is_download:
        return FileResponse(
            local_path,
            filename=custom_filename,
            media_type="application/octet-stream",
            content_disposition_type="attachment",
            headers=cors_headers
        )
    else:
        return FileResponse(
            local_path,
            media_type=content_type,
            content_disposition_type="inline",
            headers=cors_headers
        )
