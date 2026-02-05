# QR Code Command Reference

This document provides a comprehensive reference for using the `qr` command-line tool.

## Basic Usage

### Generate QR code to file
```bash
qr "Some text" > test.png
```

### Generate QR code with explicit output file
```bash
qr --output=test.png "Some text"
```

### ASCII output to terminal
```bash
qr --ascii "Some data"
```

### ASCII output to text file
```bash
qr --ascii "Some data" > test.txt
```

## Image Format Options

### PNG (default with Pillow)
```bash
qr "Some text" > test.png
qr --factory=pil "Some text" > test.png
```

### Pure Python PNG (using pypng)
```bash
qr --factory=png "Some text" > test.png
```

### SVG formats
```bash
# SVG path format (recommended, compact)
qr --factory=svg-path "Some text" > test.svg

# SVG rect format
qr --factory=svg "Some text" > test.svg

# SVG fragment (for embedding in HTML)
qr --factory=svg-fragment "Some text" > test.svg
```

## Batch Generation from CSV/Excel

### Basic batch generation
```bash
qr --csv data.csv --column 0 --output-dir ./qrcodes --skip-header
```

### Example with specific column
```bash
# Generate QR codes from column 1 (Part Number)
qr --csv "INVENTORY - Blad1.csv" --column 1 --output-dir ./inventory_qrcodes --skip-header

# Generate QR codes from column 4 (Links)
qr --csv "INVENTORY - Blad1.csv" --column 4 --output-dir ./link_qrcodes --skip-header
```

### Batch generation options explained

| Option | Description | Example |
|--------|-------------|---------|
| `--csv` | Path to CSV/Excel file | `--csv data.csv` |
| `--column` | Column index (0-based) to encode | `--column 0` |
| `--output-dir` | Directory for output files | `--output-dir ./qrcodes` |
| `--skip-header` | Skip first row (if headers present) | `--skip-header` |

### CSV file format

The CSV file should have a structure like this:

```csv
ID,Part Number,Description,Status,Links
1,ABC-123,Widget A,Active,https://example.com/abc
2,XYZ-789,Widget B,Active,https://example.com/xyz
3,DEF-456,Widget C,Inactive,https://example.com/def
```

See `INVENTORY - Blad1.csv` in the repository root for a template.

## Advanced Options

### Error correction levels
```bash
# Low (7% error correction)
qr --error-correction=L "Some text" > test.png

# Medium (15% error correction, default)
qr --error-correction=M "Some text" > test.png

# Quartile (25% error correction)
qr --error-correction=Q "Some text" > test.png

# High (30% error correction)
qr --error-correction=H "Some text" > test.png
```

### Version and size control
```bash
# Automatic version selection (default)
qr "Some text" > test.png

# Specific version (1-40)
qr --version=5 "Some text" > test.png
```

### Border and box size
```bash
# Custom border width (default is 4)
qr --border=2 "Some text" > test.png

# Custom box size (pixel size per module)
qr --box-size=20 "Some text" > test.png

# Combine options
qr --border=2 --box-size=20 "Some text" > test.png
```

## Common Use Cases

### 1. Generate QR codes for URLs
```bash
qr "https://example.com" > website.png
qr --ascii "https://example.com"
```

### 2. Generate QR codes for WiFi credentials
```bash
qr "WIFI:T:WPA;S:NetworkName;P:Password;;" > wifi.png
```

### 3. Generate QR codes for contact information (vCard)
```bash
qr "BEGIN:VCARD
VERSION:3.0
FN:John Doe
TEL:+1234567890
EMAIL:john@example.com
END:VCARD" > contact.png
```

### 4. Generate QR codes for inventory/parts database
```bash
# From Excel/CSV file with part numbers
qr --csv inventory.csv --column 1 --output-dir ./part_qrcodes --skip-header
```

### 5. Generate high-resolution QR codes
```bash
qr --box-size=30 --border=4 "Some text" > high_res.png
```

### 6. Generate compact SVG for web
```bash
qr --factory=svg-path "Some text" > compact.svg
```

## Troubleshooting

### PowerShell redirection issues
If output redirection (`>`) doesn't work properly in PowerShell, use:
```bash
qr --output=test.png "Some text"
```

### Missing image library errors
Install with PIL support:
```bash
pip install "qrcode[pil]"
```

Or for pure Python PNG:
```bash
pip install "qrcode[png]"
```

### Testing installation
```bash
# Check if qr command is available
qr --version

# Generate test QR code
qr --ascii "test"
```

## Python API Usage

For programmatic control, see the main README.rst for Python API examples.

Quick example:
```python
import qrcode
img = qrcode.make('Some data')
img.save('test.png')
```
