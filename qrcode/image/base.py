from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any

from qrcode.image.styles.moduledrawers.base import QRModuleDrawer

if TYPE_CHECKING:
    from qrcode.main import ActiveWithNeighbors, QRCode


DrawerAliases = dict[str, tuple[type[QRModuleDrawer], dict[str, Any]]]


class BaseImage(abc.ABC):
    """
    Base QRCode image output class.
    """

    kind: str | None = None
    allowed_kinds: tuple[str, ...] | None = None
    needs_context = False
    needs_processing = False
    needs_drawrect = True

    def __init__(self, border, width, box_size, *args, **kwargs):
        self.border = border
        self.width = width
        # Fixed canvas dimensions at 2x resolution for smoother output
        self.pixel_width = 288 * 2  # 576px
        self.pixel_height = 432 * 2  # 864px
        # Reserve space for ID text directly below QR code (scaled 2x)
        self.text_area_height = 120 * 2  # Larger area for bigger, smoother font
        self.text_gap = 42  # Gap reduced by 35% (from 64 to 42 pixels)

        # Get qr_size parameter if provided
        qr_size = kwargs.pop("qr_size", None)
        qr_modules = width + border * 2

        if qr_size is not None:
            # User-specified QR code size - calculate box_size to fit exactly
            self.pixel_size = int(qr_size)
            self.box_size = max(1, self.pixel_size // qr_modules)
            # Recalculate actual pixel_size based on box_size (may be slightly smaller due to rounding)
            self.pixel_size = qr_modules * self.box_size
        else:
            # Original auto-sizing logic for backward compatibility
            # Calculate box_size to fit QR code + text area (72% of canvas width max, reduced by 10%)
            max_qr_width = int(self.pixel_width * 0.72)  # Reduced by 10% from 0.8 to 0.72
            # Leave room for text area when calculating max height
            available_height = self.pixel_height - self.text_area_height - self.text_gap
            max_qr_height = int(available_height * 0.81)  # Reduced by 10% from 0.9 to 0.81
            max_qr_size = min(max_qr_width, max_qr_height)
            # Calculate appropriate box_size to fit the QR code
            self.box_size = max(1, max_qr_size // qr_modules)
            # Calculate actual QR code dimensions
            self.pixel_size = qr_modules * self.box_size

        # Calculate total content height (QR + gap + text area)
        total_content_height = self.pixel_size + self.text_gap + self.text_area_height
        # Center the entire content block (QR + text) vertically
        top_margin = (self.pixel_height - total_content_height) // 2
        # Calculate offsets
        self.qr_offset_x = (self.pixel_width - self.pixel_size) // 2  # Center horizontally
        self.qr_offset_y = top_margin  # QR code at top of content block
        self.text_offset_y = self.qr_offset_y + self.pixel_size + self.text_gap  # Text directly below QR
        self.modules = kwargs.pop("qrcode_modules")
        self._img = self.new_image(**kwargs)
        self.init_new_image()

    @abc.abstractmethod
    def drawrect(self, row, col):
        """
        Draw a single rectangle of the QR code.
        """

    def drawrect_context(self, row: int, col: int, qr: QRCode):
        """
        Draw a single rectangle of the QR code given the surrounding context
        """
        raise NotImplementedError("BaseImage.drawrect_context")  # pragma: no cover

    def process(self):
        """
        Processes QR code after completion
        """
        raise NotImplementedError("BaseImage.drawimage")  # pragma: no cover

    @abc.abstractmethod
    def save(self, stream, kind=None):
        """
        Save the image file.
        """

    def pixel_box(self, row, col):
        """
        A helper method for pixel-based image generators that specifies the
        four pixel coordinates for a single rect.
        """
        x = (col + self.border) * self.box_size + self.qr_offset_x
        y = (row + self.border) * self.box_size + self.qr_offset_y
        return (
            (x, y),
            (x + self.box_size - 1, y + self.box_size - 1),
        )

    @abc.abstractmethod
    def new_image(self, **kwargs) -> Any:
        """
        Build the image class. Subclasses should return the class created.
        """

    def init_new_image(self):  # noqa: B027
        pass

    def get_image(self, **kwargs):
        """
        Return the image class for further processing.
        """
        return self._img

    def check_kind(self, kind, transform=None):
        """
        Get the image type.
        """
        if kind is None:
            kind = self.kind
        allowed = not self.allowed_kinds or kind in self.allowed_kinds
        if transform:
            kind = transform(kind)
            if not allowed:
                allowed = kind in self.allowed_kinds
        if not allowed:
            raise ValueError(f"Cannot set {type(self).__name__} type to {kind}")
        return kind

    def is_eye(self, row: int, col: int):
        """
        Find whether the referenced module is in an eye.
        """
        return (
            (row < 7 and col < 7)
            or (row < 7 and self.width - col < 8)
            or (self.width - row < 8 and col < 7)
        )


class BaseImageWithDrawer(BaseImage):
    default_drawer_class: type[QRModuleDrawer]
    drawer_aliases: DrawerAliases = {}

    def get_default_module_drawer(self) -> QRModuleDrawer:
        return self.default_drawer_class()

    def get_default_eye_drawer(self) -> QRModuleDrawer:
        return self.default_drawer_class()

    needs_context = True

    module_drawer: QRModuleDrawer
    eye_drawer: QRModuleDrawer

    def __init__(
        self,
        *args,
        module_drawer: QRModuleDrawer | str | None = None,
        eye_drawer: QRModuleDrawer | str | None = None,
        **kwargs,
    ):
        self.module_drawer = (
            self.get_drawer(module_drawer) or self.get_default_module_drawer()
        )
        # The eye drawer can be overridden by another module drawer as well,
        # but you have to be more careful with these in order to make the QR
        # code still parseable
        self.eye_drawer = self.get_drawer(eye_drawer) or self.get_default_eye_drawer()
        super().__init__(*args, **kwargs)

    def get_drawer(self, drawer: QRModuleDrawer | str | None) -> QRModuleDrawer | None:
        if not isinstance(drawer, str):
            return drawer
        drawer_cls, kwargs = self.drawer_aliases[drawer]
        return drawer_cls(**kwargs)

    def init_new_image(self):
        self.module_drawer.initialize(img=self)
        self.eye_drawer.initialize(img=self)

        return super().init_new_image()

    def drawrect_context(self, row: int, col: int, qr: QRCode):
        box = self.pixel_box(row, col)
        drawer = self.eye_drawer if self.is_eye(row, col) else self.module_drawer
        is_active: bool | ActiveWithNeighbors = (
            qr.active_with_neighbors(row, col)
            if drawer.needs_neighbors
            else bool(qr.modules[row][col])
        )

        drawer.drawrect(box, is_active)
