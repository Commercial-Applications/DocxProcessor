"""Pre-flight checks run by both `validate` and `run` before any document is processed."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .app_config import AppConfig


@dataclass
class PreflightResult:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    document_count: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def is_within(path: Path, folder: Path) -> bool:
    """True if ``path`` is ``folder`` or inside it (after resolving)."""
    path, folder = path.resolve(), folder.resolve()
    return path == folder or folder in path.parents


def _nearest_existing(path: Path) -> Path:
    path = path.resolve()
    while not path.exists() and path != path.parent:
        path = path.parent
    return path


def preflight(config: AppConfig) -> PreflightResult:
    result = PreflightResult()
    runtime = config.runtime
    source, dest = runtime.source_dir, runtime.destination_dir

    # Source folder
    if not source.is_dir():
        result.errors.append(f"Source directory is not a directory: {source}")
    elif not os.access(source, os.R_OK):
        result.errors.append(f"Source directory is not readable: {source}")
    else:
        dest_inside = is_within(dest, source)
        result.document_count = sum(
            1
            for p in source.rglob("*.docx")
            if not p.name.startswith("~$") and not (dest_inside and is_within(p, dest))
        )
        if result.document_count == 0:
            result.warnings.append(f"No .docx files found in {source}")

    # Destination folder (only written in --modify mode)
    if not runtime.find_only:
        if is_within(dest, source):
            result.errors.append(
                f"Destination directory {dest} is the source directory or inside it; outputs would be "
                "picked up as inputs on the next run. Choose a destination outside the source directory."
            )
        if dest.exists() and not dest.is_dir():
            result.errors.append(f"Destination exists and is not a directory: {dest}")
        else:
            writable_root = _nearest_existing(dest)
            if not os.access(writable_root, os.W_OK):
                result.errors.append(f"Destination directory is not writable: {writable_root}")

    # Log file location
    log_dir = _nearest_existing(runtime.log_file.parent)
    if not os.access(log_dir, os.W_OK):
        result.errors.append(f"Log file directory is not writable: {log_dir}")

    if config.transform.is_empty:
        result.warnings.append("No url_transforms, text_transforms or style_transforms configured; nothing to do")

    return result
