"""Jewelry planner input schema + image upload validation."""
from fastapi import HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator

# Trustworthy mime sniffing via magic bytes — never rely on the client-supplied
# content type alone.
_MAGIC_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"RIFF", "image/webp"),  # RIFF....WEBP checked explicitly
)


class JewelryPlanRequest(BaseModel):
    total_budget: float = Field(gt=0, le=1_000_000_000, description="Total budget in INR")
    occasion: str = Field(min_length=2, max_length=60)
    style_preference: str | None = Field(default=None, max_length=60)
    jewelry_type: str | None = Field(default=None, max_length=60)
    outfit_description: str | None = Field(default=None, max_length=1000)

    @field_validator("occasion", "style_preference", "jewelry_type", "outfit_description")
    @classmethod
    def clean_fields(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            return v or None
        return v

    def to_input_summary(self, image_used: bool = False) -> dict:
        return {
            "occasion": self.occasion,
            "style": self.style_preference or "No preference",
            "jewelry_type": self.jewelry_type or "Open to suggestions",
            "outfit": self.outfit_description or "Not described",
            "image_analyzed": "Yes" if image_used else "No",
        }


def detect_image_mime(data: bytes, declared_type: str) -> str:
    """Return sniffed MIME type or raise when unsupported/corrupt."""
    for magic, mime in _MAGIC_SIGNATURES:
        if data.startswith(magic):
            if mime == "image/webp" and data[8:12] != b"WEBP":
                continue
            if mime != declared_type.split(";")[0].strip().lower() and declared_type not in (
                "image/jpg", "image/jpeg"
            ):
                # content-type mismatch: trust the sniffed bytes
                pass
            return mime
    raise ValueError("unsupported")


def validate_image_upload(upload: UploadFile | None, settings) -> tuple[bytes, str] | None:
    """Validate an optional jewelry outfit image.

    Returns (image_bytes, mime_type) or None when no image was uploaded.
    Raises HTTPException 400 with a human-readable message on any violation.
    """
    if upload is None or not upload.filename:
        return None

    allowed = settings.allowed_image_types
    declared = (upload.content_type or "").split(";")[0].strip().lower()
    if declared and declared not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image format. Please upload a PNG, JPG or WebP image.",
        )

    size_limit = settings.max_image_size_bytes
    data = upload.file.read(size_limit + 1)
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="The uploaded image file is empty.")
    if len(data) > size_limit:
        raise HTTPException(
            status_code=400,
            detail=f"Image is too large. Maximum allowed size is {settings.MAX_IMAGE_SIZE_MB} MB.",
        )

    sniffed = None
    for magic, mime in _MAGIC_SIGNATURES:
        if data.startswith(magic):
            if mime == "image/webp" and data[8:12] != b"WEBP":
                continue
            sniffed = "image/jpeg" if (mime == "image/jpeg" and declared == "image/jpg") else mime
            break
    if sniffed is None:
        raise HTTPException(
            status_code=400,
            detail="This file doesn't look like a valid image. Please upload a real PNG, JPG or WebP file.",
        )
    return data, sniffed
