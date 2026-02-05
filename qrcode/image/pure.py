from itertools import chain
from pathlib import Path

from qrcode.compat.png import PngWriter
from qrcode.image.base import BaseImage


class PyPNGImage(BaseImage):
    """
    pyPNG image builder.
    """

    kind = "PNG"
    allowed_kinds = ("PNG",)
    needs_drawrect = False

    def new_image(self, **kwargs):
        if not PngWriter:
            raise ImportError("PyPNG library not installed.")

        return PngWriter(self.pixel_width, self.pixel_height, greyscale=True, bitdepth=1)

    def drawrect(self, row, col):
        """
        Not used.
        """

    def save(self, stream, kind=None):
        if isinstance(stream, str):
            stream = Path(stream).open("wb")  # noqa: SIM115
        self._img.write(stream, self.rows_iter())

    def rows_iter(self):
        # Top padding to offset QR code
        for _ in range(self.qr_offset_y):
            yield self.canvas_row()
        # Border rows at top
        yield from self.border_rows_iter()
        # QR code data rows
        border_col = [1] * (self.box_size * self.border)
        left_padding = [1] * self.qr_offset_x
        right_padding = [1] * (self.pixel_width - self.qr_offset_x - self.pixel_size)
        for module_row in self.modules:
            qr_row = (
                border_col
                + list(
                    chain.from_iterable(
                        ([not point] * self.box_size) for point in module_row
                    )
                )
                + border_col
            )
            full_row = left_padding + qr_row + right_padding
            for _ in range(self.box_size):
                yield full_row
        # Border rows at bottom
        yield from self.border_rows_iter()
        # Bottom padding (remaining space including text area)
        remaining_height = self.pixel_height - self.qr_offset_y - self.pixel_size
        for _ in range(remaining_height):
            yield self.canvas_row()

    def border_rows_iter(self):
        """Generate border rows with proper horizontal padding."""
        left_padding = [1] * self.qr_offset_x
        border_section = [1] * (self.box_size * (self.width + self.border * 2))
        right_padding = [1] * (self.pixel_width - self.qr_offset_x - self.pixel_size)
        border_row = left_padding + border_section + right_padding
        for _ in range(self.border * self.box_size):
            yield border_row

    def canvas_row(self):
        """Generate a full-width white canvas row."""
        return [1] * self.pixel_width


# Keeping this for backwards compatibility.
PymagingImage = PyPNGImage
