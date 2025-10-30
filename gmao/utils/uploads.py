from __future__ import annotations

import mimetypes
import secrets
from pathlib import Path
from typing import Iterable, Mapping, Tuple

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


class UploadError(ValueError):
    """Raised when an uploaded file does not meet validation rules."""


def _normalise_mime_type(candidate: str | None, filename: str | None) -> str:
    mimetype = (candidate or "").lower()
    if mimetype:
        return mimetype
    guessed, _ = mimetypes.guess_type(filename or "")
    return (guessed or "application/octet-stream").lower()


def _ensure_allowed(mimetype: str, filename: str, allowed: Iterable[str]) -> str:
    allowed_normalised = {item.lower() for item in allowed}
    if not allowed_normalised:
        return mimetype

    if mimetype in allowed_normalised:
        return mimetype

    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf" and "application/pdf" in allowed_normalised:
        return "application/pdf"

    raise UploadError("Les pièces jointes doivent être au format PDF.")


def _generate_storage_name(filename: str) -> str:
    cleaned = secure_filename(filename)
    if not cleaned:
        raise UploadError("Nom de fichier invalide.")

    stem = Path(cleaned).stem or "document"
    suffix = Path(cleaned).suffix or ".pdf"
    token = secrets.token_hex(8)
    return f"{stem}-{token}{suffix.lower()}"


def save_job_card_file(
    file: FileStorage,
    card_id: int,
    config: Mapping[str, object],
) -> Tuple[str, str, str, str]:
    """Persist a job card attachment and return its metadata.

    Returns a tuple of ``(stored_name, relative_path, mimetype, original_name)``.
    """

    filename = file.filename or ""
    if not filename:
        raise UploadError("Aucun fichier fourni.")

    root = Path(config.get("UPLOAD_ROOT"))
    subdir = Path(config.get("JOB_CARD_UPLOAD_SUBDIR", "job_cards")) / str(card_id)
    mimetype = _normalise_mime_type(file.mimetype, filename)
    allowed = config.get("JOB_CARD_ALLOWED_MIME_TYPES", set())
    mimetype = _ensure_allowed(mimetype, filename, allowed)

    stored_name = _generate_storage_name(filename)
    relative_path = subdir / stored_name
    destination = root / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)

    file.stream.seek(0)
    file.save(destination)

    original_name = filename
    return stored_name, str(relative_path), mimetype, original_name
