#!/usr/bin/env python
"""
qr - Convert stdin (or the first argument) to a QR Code.

When stdout is a tty the QR Code is printed to the terminal and when stdout is
a pipe to a file an image is written. The default image format is PNG.
"""

from __future__ import annotations

import optparse
import os
import sys
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

import qrcode

if TYPE_CHECKING:
    from collections.abc import Iterable

    from qrcode.image.base import BaseImage, DrawerAliases

# The next block is added to get the terminal to display properly on MS platforms
if sys.platform.startswith(("win", "cygwin")):  # pragma: no cover
    import colorama

    colorama.init()

default_factories = {
    "pil": "qrcode.image.pil.PilImage",
    "png": "qrcode.image.pure.PyPNGImage",
    "svg": "qrcode.image.svg.SvgImage",
    "svg-fragment": "qrcode.image.svg.SvgFragmentImage",
    "svg-path": "qrcode.image.svg.SvgPathImage",
    # Keeping for backwards compatibility:
    "pymaging": "qrcode.image.pure.PymagingImage",
}

error_correction = {
    "L": qrcode.ERROR_CORRECT_L,
    "M": qrcode.ERROR_CORRECT_M,
    "Q": qrcode.ERROR_CORRECT_Q,
    "H": qrcode.ERROR_CORRECT_H,
}


def generate_from_csv(
    csv_path: str,
    output_dir: str,
    column: int,
    factory: str | None,
    error_correction_level: str,
    base_url: str,
    skip_header: bool = False,
    qr_size: int | None = None,
) -> None:
    """Generate QR codes from CSV file data."""
    import csv

    # Read data from CSV file
    values = []
    try:
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            if skip_header:
                next(reader, None)  # Skip the header row
            for row in reader:
                if len(row) > column:
                    values.append([row[column]])
    except FileNotFoundError:
        print(f"Error: CSV file not found: {csv_path}")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    if not values:
        print("No data found in the specified column.")
        return

    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Set up image factory - use PIL for text support
    if factory:
        module = default_factories.get(factory, factory)
        try:
            image_factory = get_factory(module)
        except ValueError as e:
            raise ValueError(str(e)) from e
    else:
        # Default to PIL for batch generation (supports text labels)
        try:
            image_factory = get_factory("qrcode.image.pil.PilImage")
        except ImportError:
            print("PIL/Pillow not available, falling back to SVG (no text labels)")
            image_factory = get_factory("qrcode.image.svg.SvgPathImage")

    # Generate QR codes
    error_corr = error_correction[error_correction_level]
    count = 0

    for row in values:
        if not row or not row[0].strip():
            continue

        part_number = row[0].strip()
        # Sanitize filename - replace invalid characters
        safe_filename = "".join(
            c if c.isalnum() or c in "._- " else "_" for c in part_number
        )
        output_file = output_path / f"{safe_filename}.png"

        # Build full URL with part number
        full_url = f"{base_url}?part={part_number}"

        # Generate QR code
        qr = qrcode.QRCode(
            error_correction=error_corr,
            image_factory=image_factory,
            border=4,
            qr_size=qr_size,
        )
        qr.add_data(full_url)
        qr.make(fit=True)

        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")

        # Add text label below QR code if using PIL
        if hasattr(img, '_img'):  # Check if it's a PIL image
            from PIL import Image, ImageDraw, ImageFont, ImageOps

            # First, rotate the QR code portion 90 degrees counter-clockwise
            qr_region = img._img.crop((
                img.qr_offset_x,
                img.qr_offset_y,
                img.qr_offset_x + img.pixel_size,
                img.qr_offset_y + img.pixel_size
            ))
            qr_rotated = qr_region.transpose(Image.ROTATE_270)
            img._img.paste(qr_rotated, (img.qr_offset_x, img.qr_offset_y))

            # Draw text directly on the existing image in the allocated text area
            draw = ImageDraw.Draw(img._img)

            # Use a much larger font size for better rendering quality (scaled for 2x canvas, increased by 25%)
            font_size = 100  # Increased by 25% from 80 to 100
            font = None

            # Try multiple font locations - prefer very smooth, modern fonts
            font_paths = [
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Clean sans-serif
                "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Regular weight is smoother
                "/usr/share/fonts/TTF/DejaVuSans.ttf",
                "/usr/share/fonts/noto/NotoSans-Regular.ttf",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-Regular.ttf",
                "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf",
                "/usr/share/fonts/google-noto/NotoSans-Regular.ttf",
            ]

            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue

            if font is None:
                print(f"WARNING: Could not load TrueType font. Using default font.")
                print(f"Install fonts with: sudo pacman -S ttf-dejavu")
                font = ImageFont.load_default()
                font_size = 80  # Fallback size for default font at 2x resolution

            # Render vector font at very high resolution for ultra-smooth rasterization
            # Calculate proper size based on actual text measurement
            bbox = draw.textbbox((0, 0), part_number, font=font, anchor='mm')
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Add padding
            padding = 40
            target_width = text_width + padding * 2
            target_height = text_height + padding * 2

            # Render at 20x resolution for ultra-smooth vector rasterization
            scale = 20
            hr_width = target_width * scale
            hr_height = target_height * scale

            # Create very high-res grayscale image for superior anti-aliasing
            text_img_hr = Image.new('L', (hr_width, hr_height), 255)
            text_draw_hr = ImageDraw.Draw(text_img_hr)

            # Load font at scaled size
            font_hr = ImageFont.truetype(font.path, font_size * scale)

            # Draw text centered in high-res image (grayscale for better AA)
            text_center_x = hr_width // 2
            text_center_y = hr_height // 2
            text_draw_hr.text((text_center_x, text_center_y), part_number, fill=0, font=font_hr, anchor='mm')

            # Downsample with LANCZOS for ultra-smooth result
            text_img_gray = text_img_hr.resize((target_width, target_height), Image.Resampling.LANCZOS)

            # Convert to RGB
            text_img = Image.new('RGB', (target_width, target_height), 'white')
            text_img.paste(Image.new('RGB', text_img_gray.size, 'black'), mask=ImageOps.invert(text_img_gray))

            # Rotate text 90 degrees counter-clockwise
            text_rotated = text_img.transpose(Image.ROTATE_270)

            # Calculate position to center the rotated text in the text area
            # After rotation, width and height are swapped
            rotated_width = text_rotated.width
            rotated_height = text_rotated.height

            text_x = img.qr_offset_x + (img.pixel_size - rotated_width) // 2
            text_y = img.text_offset_y + (img.text_area_height - rotated_height) // 2

            # Paste the rotated text
            img._img.paste(text_rotated, (text_x, text_y))

            # Save the image (already has text drawn on it)
            img.save(output_file)
        else:
            # Fallback for non-PIL images (SVG)
            with output_file.open("wb") as f:
                img.save(f)

        count += 1
        print(f"Generated: {output_file} -> {full_url}")

    print(f"\nSuccessfully generated {count} QR codes in '{output_dir}/'")


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    version = metadata.version("qrcode")
    parser = optparse.OptionParser(usage=(__doc__ or "").strip(), version=version)

    # Wrap parser.error in a typed NoReturn method for better typing.
    def raise_error(msg: str) -> NoReturn:
        parser.error(msg)
        raise  # pragma: no cover # noqa: PLE0704

    parser.add_option(
        "--factory",
        help="Full python path to the image factory class to "
        "create the image with. You can use the following shortcuts to the "
        f"built-in image factory classes: {commas(default_factories)}.",
    )
    parser.add_option(
        "--factory-drawer",
        help=f"Use an alternate drawer. {get_drawer_help()}.",
    )
    parser.add_option(
        "--optimize",
        type=int,
        help="Optimize the data by looking for chunks "
        "of at least this many characters that could use a more efficient "
        "encoding method. Use 0 to turn off chunk optimization.",
    )
    parser.add_option(
        "--error-correction",
        type="choice",
        choices=sorted(error_correction.keys()),
        default="M",
        help="The error correction level to use. Choices are L (7%), "
        "M (15%, default), Q (25%), and H (30%).",
    )
    parser.add_option(
        "--ascii", help="Print as ascii even if stdout is piped.", action="store_true"
    )
    parser.add_option(
        "--output",
        help="The output file. If not specified, the image is sent to "
        "the standard output.",
    )
    parser.add_option(
        "--csv",
        help="Path to CSV file to read data from.",
    )
    parser.add_option(
        "--output-dir",
        help="Output directory for QR codes when using --csv. Defaults to 'qr_codes'.",
        default="qr_codes",
    )
    parser.add_option(
        "--column",
        help="Column index to read from (0-based). Defaults to 0.",
        type=int,
        default=0,
    )
    parser.add_option(
        "--skip-header",
        help="Skip the first row of the CSV file (header row).",
        action="store_true",
        default=False,
    )
    parser.add_option(
        "--base-url",
        help="Base URL template for QR codes. Part number will be appended as ?part=VALUE. "
        "Defaults to Google Apps Script URL.",
        default="https://script.google.com/macros/s/AKfycbxeY8GP1xl9xF_Fn7rdGeah90fFa07hauK30GvXfdtoUO4gHE9mPdIn25XaFRADWpUhoA/exec",
    )
    parser.add_option(
        "--qr-size",
        type=int,
        help="The pixel length of one side of the square QR code. "
        "If not specified, the size will be calculated automatically to fit the frame.",
    )

    opts, args = parser.parse_args(args)

    # Handle CSV mode
    if opts.csv:
        generate_from_csv(
            csv_path=opts.csv,
            output_dir=opts.output_dir,
            column=opts.column,
            factory=opts.factory,
            error_correction_level=opts.error_correction,
            base_url=opts.base_url,
            skip_header=opts.skip_header,
            qr_size=opts.qr_size,
        )
        return

    if opts.factory:
        module = default_factories.get(opts.factory, opts.factory)
        try:
            image_factory = get_factory(module)
        except ValueError as e:
            raise_error(str(e))
    else:
        image_factory = None

    qr = qrcode.QRCode(
        error_correction=error_correction[opts.error_correction],
        image_factory=image_factory,
        qr_size=opts.qr_size,
    )

    if args:
        data = args[0]
        data = data.encode(errors="surrogateescape")
    else:
        data = sys.stdin.buffer.read()
    if opts.optimize is None:
        qr.add_data(data)
    else:
        qr.add_data(data, optimize=opts.optimize)

    if opts.output:
        img = qr.make_image()
        with Path(opts.output).open("wb") as out:
            img.save(out)
    else:
        if image_factory is None and (os.isatty(sys.stdout.fileno()) or opts.ascii):
            qr.print_ascii(tty=not opts.ascii)
            return

        kwargs = {}
        aliases: DrawerAliases | None = getattr(
            qr.image_factory, "drawer_aliases", None
        )
        if opts.factory_drawer:
            if not aliases:
                raise_error("The selected factory has no drawer aliases.")
            if opts.factory_drawer not in aliases:
                raise_error(
                    f"{opts.factory_drawer} factory drawer not found."
                    f" Expected {commas(aliases)}"
                )
            drawer_cls, drawer_kwargs = aliases[opts.factory_drawer]
            kwargs["module_drawer"] = drawer_cls(**drawer_kwargs)
        img = qr.make_image(**kwargs)

        sys.stdout.flush()
        img.save(sys.stdout.buffer)


def get_factory(module: str) -> type[BaseImage]:
    if "." not in module:
        raise ValueError("The image factory is not a full python path")
    module, name = module.rsplit(".", 1)
    imp = __import__(module, {}, {}, [name])
    return getattr(imp, name)


def get_drawer_help() -> str:
    help: dict[str, set] = {}

    for alias, module in default_factories.items():
        try:
            image = get_factory(module)
        except ImportError:  # pragma: no cover
            continue
        aliases: DrawerAliases | None = getattr(image, "drawer_aliases", None)
        if not aliases:
            continue
        factories = help.setdefault(commas(aliases), set())
        factories.add(alias)

    return ". ".join(
        f"For {commas(factories, 'and')}, use: {aliases}"
        for aliases, factories in help.items()
    )


def commas(items: Iterable[str], joiner="or") -> str:
    items = tuple(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} {joiner} {items[-1]}"


if __name__ == "__main__":  # pragma: no cover
    main()
