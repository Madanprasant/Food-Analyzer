from __future__ import annotations

from pathlib import Path
from uuid import uuid4


class LocalImageStorage:
    """Development storage adapter; production object storage can replace it."""

    def __init__(self, upload_dir: Path) -> None:
        self.upload_dir = upload_dir

    def save(self, content: bytes, suffix: str) -> str:
        safe_suffix = suffix.lower() if suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"
        filename = f"{uuid4().hex}{safe_suffix}"
        target = self.upload_dir / filename
        target.write_bytes(content)
        return filename

    def delete(self, image_reference: str | None) -> None:
        if not image_reference:
            return
        candidate = self.upload_dir / Path(image_reference).name
        if candidate.is_file():
            candidate.unlink()
