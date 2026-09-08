from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile

MAX_PHOTO_BYTES = 2 * 1024 * 1024
PHOTO_ROOT = Path(__file__).resolve().parents[3] / "media" / "students"
ALLOWED = {
    "image/jpeg": ("jpg", b"\xff\xd8\xff"),
    "image/png": ("png", b"\x89PNG\r\n\x1a\n"),
    "image/webp": ("webp", b"RIFF"),
}


def _valid_signature(content_type: str, header: bytes) -> bool:
    if content_type not in ALLOWED:
        return False
    extension, signature = ALLOWED[content_type]
    if extension == "webp":
        return header.startswith(signature) and len(header) >= 12 and header[8:12] == b"WEBP"
    return header.startswith(signature)


async def save_student_photo(tenant_id: UUID, student_id: UUID, upload: UploadFile) -> tuple[str, str, int]:
    content_type = (upload.content_type or "").lower()
    if content_type not in ALLOWED:
        raise HTTPException(415, "Student photo must be JPEG, PNG or WebP")

    header = await upload.read(12)
    if not _valid_signature(content_type, header):
        raise HTTPException(415, "The uploaded file is not a valid image")
    await upload.seek(0)

    data = bytearray()
    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > MAX_PHOTO_BYTES:
            raise HTTPException(413, "Student photo must not exceed 2 MB")

    extension = ALLOWED[content_type][0]
    directory = PHOTO_ROOT / str(tenant_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{student_id}.{extension}"

    for old in directory.glob(f"{student_id}.*"):
        if old != path and old.is_file():
            old.unlink(missing_ok=True)
    path.write_bytes(data)
    return str(path), f"/api/v1/students/{student_id}/photo", len(data)


def photo_path(tenant_id: UUID, student_id: UUID) -> Path:
    directory = PHOTO_ROOT / str(tenant_id)
    for extension in ("jpg", "png", "webp"):
        candidate = directory / f"{student_id}.{extension}"
        if candidate.is_file():
            return candidate
    raise HTTPException(404, "Student photo not found")
