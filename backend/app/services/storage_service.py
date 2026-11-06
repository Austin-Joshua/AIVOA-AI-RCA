import os
import re
import uuid
import hashlib
import logging
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".log", ".csv", ".eml", ".json"}
PDF_MAGIC_BYTES = b"%PDF"

class FileIntegrityError(Exception):
    """Raised when on-disk file checksum does not match registered checksum."""
    pass

class StorageService:
    def __init__(self):
        self.base_dir = Path(settings.EVIDENCE_STORAGE_DIR).resolve()
        self.max_size_bytes = settings.MAX_UPLOAD_SIZE_BYTES
        os.makedirs(self.base_dir, exist_ok=True)

    def sanitize_filename(self, filename: str) -> str:
        """Strips path traversal attempts and special characters, preserving extension."""
        if not filename:
            return "unnamed_document"
        # Take basename only
        base = os.path.basename(filename)
        # Remove traversal sequences and null bytes
        base = base.replace("..", "").replace("/", "").replace("\\", "").replace("\x00", "")
        # Normalize characters
        base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
        return base or "unnamed_document"

    async def read_and_validate_upload(self, file: UploadFile) -> Tuple[bytes, str, str]:
        """
        Reads file stream in chunks enforcing MAX_UPLOAD_SIZE_BYTES.
        Validates extension and file magic bytes.
        Returns: (file_bytes, safe_filename, extension)
        """
        raw_filename = file.filename or "uploaded_file"
        safe_filename = self.sanitize_filename(raw_filename)
        _, ext = os.path.splitext(safe_filename.lower())

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Allowed formats: {sorted(list(ALLOWED_EXTENSIONS))}"
            )

        # Chunked read to prevent unbounded memory consumption
        chunks = []
        total_bytes = 0
        chunk_size = 64 * 1024  # 64 KB

        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > self.max_size_bytes:
                max_mb = self.max_size_bytes // (1024 * 1024)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum allowed upload size of {max_mb} MB."
                )
            chunks.append(chunk)

        file_bytes = b"".join(chunks)

        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file upload rejected."
            )

        # File signature / magic bytes verification
        if ext == ".pdf":
            if not file_bytes.startswith(PDF_MAGIC_BYTES):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Malformed PDF: Missing standard %PDF file header signature."
                )
        else:
            # Check text encodability for text-based extensions
            try:
                file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    file_bytes.decode("latin-1")
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Binary content detected in non-PDF file extension '{ext}'."
                    )

        return file_bytes, safe_filename, ext

    def save_evidence_file(self, investigation_id: int, original_filename: str, file_bytes: bytes) -> Tuple[str, str]:
        """
        Saves file bytes to an isolated investigation storage folder.
        Returns: (relative_or_absolute_file_path, file_hash_sha256)
        """
        inv_dir = self.base_dir / str(investigation_id)
        os.makedirs(inv_dir, exist_ok=True)

        safe_filename = self.sanitize_filename(original_filename)
        unique_prefix = uuid.uuid4().hex[:12]
        stored_filename = f"{unique_prefix}_{safe_filename}"
        target_path = inv_dir / stored_filename

        try:
            with open(target_path, "wb") as f:
                f.write(file_bytes)
        except Exception as e:
            logger.error(f"Failed to persist evidence file to {target_path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to persist evidence file: {e}"
            )

        file_hash = hashlib.sha256(file_bytes).hexdigest()
        return str(target_path), file_hash

    def retrieve_and_verify_file(self, file_path_str: str, expected_hash: str) -> bytes:
        """
        Reads evidence file from disk and recalculates SHA-256.
        Raises FileIntegrityError if hash does not match expected_hash.
        """
        path = Path(file_path_str).resolve()

        # Security check: ensure path is within base_dir to prevent arbitrary file reading
        try:
            path.relative_to(self.base_dir)
        except ValueError:
            logger.error(f"Path traversal detected or file outside evidence root: {path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to specified file path is forbidden."
            )

        if not path.is_file():
            logger.error(f"Stored evidence file missing on disk: {path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original evidence file not found on disk."
            )

        with open(path, "rb") as f:
            disk_bytes = f.read()

        computed_hash = hashlib.sha256(disk_bytes).hexdigest()
        if expected_hash and computed_hash.lower() != expected_hash.lower():
            logger.critical(
                f"INTEGRITY ALERT: SHA-256 mismatch for {path}. Expected: {expected_hash}, Computed: {computed_hash}"
            )
            raise FileIntegrityError(
                f"Evidence file integrity check failed: SHA-256 fingerprint mismatch. "
                f"Stored: {expected_hash}, Actual: {computed_hash}"
            )

        return disk_bytes

storage_service = StorageService()

