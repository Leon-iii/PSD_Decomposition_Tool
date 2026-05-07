from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUPPORTED_EXTENSIONS = {".psd"}


@dataclass(frozen=True)
class LayerInfo:
    id: str
    name: str
    path: tuple[str, ...]
    visible: bool
    width: int
    height: int
    left: int = 0
    top: int = 0

    @property
    def display_name(self) -> str:
        return " / ".join((*self.path, self.name)) if self.path else self.name


@dataclass(frozen=True)
class ExportJob:
    source_path: Path
    output_directory: Path
    wrap_with_folder: bool
    include_original_name: bool
    include_layer_name: bool
    include_date: bool
    overwrite_existing: bool
    export_format: str
    rescale: int
    preserve_canvas: bool
    selected_layer_ids: tuple[str, ...]
