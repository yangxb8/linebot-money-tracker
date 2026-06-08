# Sample Receipt OCR Corpus

This directory contains sample OCR text outputs for unit testing the deterministic receipt parser and hybrid AI-assist flow. These are plain-text representations of receipt OCR output (not image files) so tests can run without external OCR services.

## Files

| File | Description |
|------|-------------|
| `simple_thai_receipt.ocr.txt` | Single-line Thai cafe receipt |
| `multi_line_receipt.ocr.txt` | Multi-line grocery receipt with several items |
| `usd_receipt.ocr.txt` | US dollar receipt with `$` symbol |
| `japanese_receipt.ocr.txt` | Japanese convenience store receipt with 円 suffix |
| `my_basket_receipt.ocr.txt` | My Basket (まいばすけっと) receipt with ※ tax-marker prices and 合計 |

## Usage

Load a sample in tests:

```python
from pathlib import Path

sample = Path('specs/002-expense-intent-analysis/samples/simple_thai_receipt.ocr.txt').read_text()
items = parse_text_for_expenses(sample)
```

## Adding Samples

When adding new samples, prefer realistic OCR noise (extra spaces, line breaks) over perfectly formatted text. This helps validate parser robustness.
