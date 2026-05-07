from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .models import LayerInfo, SUPPORTED_EXTENSIONS


class PsdBackendError(RuntimeError):
    pass


def validate_input_path(path: Path) -> None:
    if not path.exists():
        raise PsdBackendError(f"파일이 존재하지 않습니다: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise PsdBackendError(f"지원하지 않는 확장자입니다. 지원 형식: {supported}")


class PsdDocument:
    def __init__(self, path: Path) -> None:
        validate_input_path(path)
        try:
            from psd_tools import PSDImage
        except ImportError as exc:
            raise PsdBackendError(
                "PSD 파일을 읽으려면 psd-tools가 필요합니다. requirements.txt를 먼저 설치하세요."
            ) from exc

        self.path = path
        self._psd = PSDImage.open(path)
        self.width, self.height = self._get_canvas_size()
        self.layers = tuple(self._collect_layers())
        self._layers_by_id = {layer.id: layer for layer in self.layers}

    def _get_canvas_size(self) -> tuple[int, int]:
        size = getattr(self._psd, "size", None)
        if size:
            return int(size[0]), int(size[1])
        return int(getattr(self._psd, "width", 0)), int(getattr(self._psd, "height", 0))

    def _collect_layers(self) -> Iterable[LayerInfo]:
        counter = 0

        def walk(nodes: Iterable[Any], group_path: tuple[str, ...]) -> Iterable[LayerInfo]:
            nonlocal counter
            for node in nodes:
                name = str(getattr(node, "name", "") or f"레이어 {counter + 1}")
                if getattr(node, "is_group", lambda: False)():
                    yield from walk(node, (*group_path, name))
                    continue

                left, top, right, bottom = getattr(node, "bbox", (0, 0, 0, 0))
                layer_id = str(counter)
                counter += 1
                yield LayerInfo(
                    id=layer_id,
                    name=name,
                    path=group_path,
                    visible=bool(getattr(node, "visible", True)),
                    width=max(0, int(right) - int(left)),
                    height=max(0, int(bottom) - int(top)),
                    left=int(left),
                    top=int(top),
                )

        return walk(self._psd, ())

    def get_layer_node(self, layer_id: str) -> Any:
        target_index = int(layer_id)
        index = 0

        def walk(nodes: Iterable[Any]) -> Any | None:
            nonlocal index
            for node in nodes:
                if getattr(node, "is_group", lambda: False)():
                    found = walk(node)
                    if found is not None:
                        return found
                    continue
                if index == target_index:
                    return node
                index += 1
            return None

        node = walk(self._psd)
        if node is None:
            raise PsdBackendError(f"레이어 ID를 찾을 수 없습니다: {layer_id}")
        return node

    def get_layer_info(self, layer_id: str) -> LayerInfo:
        try:
            return self._layers_by_id[layer_id]
        except KeyError as exc:
            raise PsdBackendError(f"레이어 ID를 찾을 수 없습니다: {layer_id}") from exc

    def render_layer(self, layer_id: str):
        node = self.get_layer_node(layer_id)
        image = node.composite()
        if image is None:
            raise PsdBackendError(f"레이어를 렌더링할 수 없습니다: {self.get_layer_info(layer_id).display_name}")
        return image

    def render_preview(self):
        image = self._psd.composite()
        if image is None:
            raise PsdBackendError("PSD 미리보기 이미지를 생성할 수 없습니다.")
        return image

    def render_layer_thumbnail(self, layer_id: str, max_size: tuple[int, int] = (48, 48)):
        image = self.render_layer(layer_id).convert("RGBA")
        image.thumbnail(max_size)
        return image
