from __future__ import annotations

import unittest

from PIL import Image

from psd_decomposer.exporter import Exporter
from psd_decomposer.models import LayerInfo


class FakeDocument:
    width = 6
    height = 5

    def __init__(self, layer: LayerInfo, image: Image.Image) -> None:
        self.layer = layer
        self.image = image

    def get_layer_info(self, _layer_id: str) -> LayerInfo:
        return self.layer

    def render_layer(self, _layer_id: str) -> Image.Image:
        return self.image


class ExporterImageTests(unittest.TestCase):
    def test_prepare_png_image_preserves_canvas_and_position(self) -> None:
        layer = LayerInfo(id="0", name="box", path=(), visible=True, width=2, height=2, left=3, top=1)
        layer_image = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
        output = Exporter._prepare_png_image(FakeDocument(layer, layer_image), "0", preserve_canvas=True)

        self.assertEqual(output.size, (6, 5))
        self.assertEqual(output.getpixel((3, 1)), (255, 0, 0, 255))
        self.assertEqual(output.getpixel((2, 1)), (0, 0, 0, 0))

    def test_prepare_png_image_can_crop_to_layer_object(self) -> None:
        layer = LayerInfo(id="0", name="box", path=(), visible=True, width=2, height=2, left=3, top=1)
        layer_image = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
        output = Exporter._prepare_png_image(FakeDocument(layer, layer_image), "0", preserve_canvas=False)

        self.assertEqual(output.size, (2, 2))


if __name__ == "__main__":
    unittest.main()

