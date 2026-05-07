from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable

from PIL import Image

from .models import ExportJob
from .naming import build_base_name, build_output_directory, resolve_output_path
from .psd_backend import PsdBackendError, PsdDocument


ProgressCallback = Callable[[str], None]


class Exporter:
    def __init__(self, progress: ProgressCallback | None = None) -> None:
        self.progress = progress or (lambda _message: None)

    def export(self, job: ExportJob) -> list[Path]:
        if not job.selected_layer_ids:
            raise PsdBackendError("내보낼 레이어를 하나 이상 선택하세요.")

        document = PsdDocument(job.source_path)
        output_directory = build_output_directory(job)
        output_directory.mkdir(parents=True, exist_ok=True)

        if job.export_format == "PNG":
            return self._export_png(document, job, output_directory)
        if job.export_format == "PSD":
            return self._export_psd(document, job, output_directory)
        raise PsdBackendError(f"지원하지 않는 출력 형식입니다: {job.export_format}")

    def _export_png(self, document: PsdDocument, job: ExportJob, output_directory: Path) -> list[Path]:
        outputs: list[Path] = []
        scale = job.rescale / 100
        reserved_paths: set[Path] = set()

        for layer_id in job.selected_layer_ids:
            layer = document.get_layer_info(layer_id)
            self.progress(f"PNG 렌더링 중: {layer.display_name}")
            image = self._prepare_png_image(document, layer_id, job.preserve_canvas)
            if scale != 1:
                width = max(1, round(image.width * scale))
                height = max(1, round(image.height * scale))
                image = image.resize((width, height), Image.Resampling.LANCZOS)

            base_name = build_base_name(job, layer)
            output_path = resolve_output_path(
                output_directory,
                base_name,
                "png",
                job.overwrite_existing,
                reserved_paths,
            )
            image.save(output_path)
            outputs.append(output_path)

        return outputs

    @staticmethod
    def _prepare_png_image(document: PsdDocument, layer_id: str, preserve_canvas: bool) -> Image.Image:
        layer = document.get_layer_info(layer_id)
        image = document.render_layer(layer_id).convert("RGBA")
        if not preserve_canvas:
            return image
        if image.size == (document.width, document.height):
            return image

        canvas = Image.new("RGBA", (document.width, document.height), (0, 0, 0, 0))
        source_left = max(0, -layer.left)
        source_top = max(0, -layer.top)
        dest_left = max(0, layer.left)
        dest_top = max(0, layer.top)
        width = min(image.width - source_left, document.width - dest_left)
        height = min(image.height - source_top, document.height - dest_top)
        if width > 0 and height > 0:
            cropped = image.crop((source_left, source_top, source_left + width, source_top + height))
            canvas.alpha_composite(cropped, dest=(dest_left, dest_top))
        return canvas

    def _export_psd(self, document: PsdDocument, job: ExportJob, output_directory: Path) -> list[Path]:
        try:
            import win32com.client
        except ImportError as exc:
            raise PsdBackendError(
                "PSD 내보내기는 Windows의 pywin32와 설치된 Photoshop이 필요합니다. "
                "PNG 내보내기는 Photoshop 없이 사용할 수 있습니다."
            ) from exc

        app = win32com.client.Dispatch("Photoshop.Application")
        outputs: list[Path] = []
        reserved_paths: set[Path] = set()

        for layer_id in job.selected_layer_ids:
            layer = document.get_layer_info(layer_id)
            base_name = build_base_name(job, layer)
            output_path = resolve_output_path(
                output_directory,
                base_name,
                "psd",
                job.overwrite_existing,
                reserved_paths,
            )
            shutil.copy2(job.source_path, output_path)
            self.progress(f"PSD 준비 중: {layer.display_name}")
            self._keep_only_layer_in_photoshop(app, output_path, layer.display_name, job.rescale, job.preserve_canvas)
            outputs.append(output_path)

        return outputs

    @staticmethod
    def _keep_only_layer_in_photoshop(
        app, path: Path, layer_display_name: str, rescale: int, preserve_canvas: bool
    ) -> None:
        doc = app.Open(str(path))
        try:
            target_path_json = json.dumps(layer_display_name)
            scale = rescale / 100
            script = f"""
var targetPath = {target_path_json};
var targetParts = targetPath.split(" / ");

function visit(container, ancestors) {{
    for (var i = container.layers.length - 1; i >= 0; i--) {{
        var layer = container.layers[i];
        var current = ancestors.concat([layer.name]);
        if (layer.typename == "ArtLayer") {{
            if (current.join(" / ") != targetPath) {{
                layer.remove();
            }}
        }} else {{
            visit(layer, current);
            if (layer.layers.length == 0) {{
                layer.remove();
            }}
        }}
    }}
}}

visit(app.activeDocument, []);
if (!{json.dumps(preserve_canvas)}) {{
    app.activeDocument.trim(TrimType.TRANSPARENT, true, true, true, true);
}}
if ({scale} != 1) {{
    app.activeDocument.resizeImage(
        UnitValue(app.activeDocument.width.value * {scale}, "px"),
        UnitValue(app.activeDocument.height.value * {scale}, "px"),
        null,
        ResampleMethod.BICUBIC
    );
}}
"""
            app.DoJavaScript(script)
            doc.Save()
        finally:
            doc.Close(2)
