# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

python-qrcode is a pure Python QR Code generator library that supports multiple output formats (PNG, SVG, PIL images) and advanced styling options. The library provides both a programmatic API and a command-line interface.

## Development Commands

### Setup
```bash
# Install dependencies with Poetry
poetry install --with dev

# Install with specific extras
pip install "qrcode[pil]"  # For PIL/Pillow support
pip install "qrcode[png]"  # For pypng support
```

### Testing
```bash
# Run all tests
poetry run pytest --cov

# Run tests with tox (all Python versions and dependency combinations)
poetry run tox

# Test specific Python version and dependency
tox -e py312-pil

# Run tests without coverage
pytest
```

### Linting
```bash
# Check and fix formatting with ruff
ruff format qrcode

# Run ruff linting
ruff check qrcode
```

### Running the CLI
```bash
# Generate QR code to stdout
qr "Some text" > test.png

# ASCII output
qr --ascii "Some data"

# Different image factories
qr --factory=svg-path "Some text" > test.svg
qr --factory=pil "Some text" > test.png

# Batch generation from CSV
qr --csv data.csv --column 0 --output-dir qrcodes --skip-header
```

## Architecture

### Core Components

**QRCode class (`qrcode/main.py`)**
- Main entry point for QR code generation
- Handles QR code data encoding, version selection, error correction
- Uses a modular image factory pattern for different output formats
- The `modules` attribute is a 2D list representing the QR code matrix (True/False for black/white)
- Supports mask pattern selection and auto-fitting to optimal version

**Image Factory Pattern (`qrcode/image/`)**
- All image factories inherit from `BaseImage` (`qrcode/image/base.py`)
- Factory types:
  - `PilImage`: Uses Pillow for PNG/JPEG output
  - `PyPNGImage`: Pure Python PNG using pypng (no external dependencies)
  - `SvgImage`, `SvgPathImage`, `SvgFragmentImage`: SVG variants
  - `StyledPilImage`: Supports custom module drawers and color masks
- Image factories are instantiated via the `image_factory` parameter

**Module Drawers (`qrcode/image/styles/moduledrawers/`)**
- Control the shape of individual QR code modules (squares, circles, rounded corners)
- Separate implementations for PIL (`pil.py`) and SVG (`svg.py`)
- Base class in `base.py` defines the drawer interface

**Color Masks (`qrcode/image/styles/colormasks.py`)**
- Apply color transformations to styled QR codes
- Support for gradients, solid colors, and custom color patterns
- Only work with `StyledPilImage`

**Console Scripts (`qrcode/console_scripts.py`)**
- Implements the `qr` CLI command
- Handles output detection (terminal vs file)
- Supports CSV batch processing
- Auto-selects appropriate image factory based on available dependencies

### Key Design Patterns

**Auto-fallback Image Factory Selection**
The library automatically selects the best available image factory:
1. If Pillow is installed → `PilImage` (default)
2. Otherwise → `PyPNGImage` (pure Python fallback)

**Version Auto-fitting**
QR codes have versions 1-40 (21×21 to 177×177 modules). When `version=None`, the library calls `best_fit()` to automatically select the smallest version that fits the data.

**Module Caching**
The `precomputed_qr_blanks` cache in `main.py` stores blank QR code templates by version to avoid regenerating the fixed patterns.

### Important File Locations

- `qrcode/constants.py`: Error correction levels, mode constants
- `qrcode/exceptions.py`: Custom exception types
- `qrcode/util.py`: QR code encoding utilities (Reed-Solomon, bit manipulation)
- `qrcode/LUT.py`: Lookup tables for QR code generation
- `qrcode/base.py`: Low-level QR code data structures
- `qrcode/compat/`: Compatibility layer for optional dependencies (etree, png)

## Testing Notes

- Tests are in `qrcode/tests/`
- Regression tests in `qrcode/tests/regression/`
- Test matrix covers Python 3.9-3.13 with three dependency scenarios: pil, png, none
- Coverage reporting is enabled by default
- Some tests may require specific image libraries (PIL/pypng)

## Ruff Configuration

The project uses ruff for linting with extensive customization in `pyproject.toml`:
- Target: Python 3.9+
- Many rules disabled for legacy code (see `lint.ignore` section)
- Special per-file ignores for test files
- Formatted with ruff format (replaces black)
