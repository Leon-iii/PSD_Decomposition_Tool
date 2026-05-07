from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from .models import ExportJob, LayerInfo


INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename_part(value: str) -> str:
    cleaned = INVALID_FILENAME_CHARS.sub("_", value).strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or "layer"


def build_output_directory(job: ExportJob) -> Path:
    directory = job.output_directory
    if job.wrap_with_folder:
        directory = directory / f"{sanitize_filename_part(job.source_path.stem)}_decomposed"
    return directory


def build_base_name(job: ExportJob, layer: LayerInfo, today: date | None = None) -> str:
    today = today or date.today()
    parts: list[str] = []
    if job.include_original_name:
        parts.append(job.source_path.stem)
    if job.include_layer_name:
        parts.append(layer.name)
    if job.include_date:
        parts.append(today.strftime("%y%m%d"))

    if not parts:
        parts.append(layer.name)
    return "_".join(sanitize_filename_part(part) for part in parts)


def unique_output_path(directory: Path, base_name: str, extension: str) -> Path:
    extension = extension.lower().lstrip(".")
    candidate = directory / f"{base_name}.{extension}"
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        candidate = directory / f"{base_name}_{index}.{extension}"
        if not candidate.exists():
            return candidate
        index += 1


def resolve_output_path(
    directory: Path,
    base_name: str,
    extension: str,
    overwrite_existing: bool,
    reserved_paths: set[Path],
) -> Path:
    extension = extension.lower().lstrip(".")
    candidate = directory / f"{base_name}.{extension}"
    if candidate not in reserved_paths and (overwrite_existing or not candidate.exists()):
        reserved_paths.add(candidate)
        return candidate

    index = 2
    while True:
        candidate = directory / f"{base_name}_{index}.{extension}"
        if candidate not in reserved_paths and (overwrite_existing or not candidate.exists()):
            reserved_paths.add(candidate)
            return candidate
        index += 1
