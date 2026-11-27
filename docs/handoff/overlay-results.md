# Synthetic overlay comparison

The fixed-layout reader and Tesseract 5.3.4 read the same cropped timestamp
strips. Tesseract used three-times enlargement and single-line mode.
Character errors are Levenshtein edit distances from the known overlay.

| Frame | Built-in result | Tesseract result | Character errors |
| --- | --- | --- | --- |
| CAM-A entrance | 03-12-2025 22:06:20 | 03-12-2025 22:06:20 | 0 for both |
| CAM-B corridor | 03-12-2025 22:05:40 | 03-12-2025 22:05:40 | 0 for both |
| Blurry CAM-B | Manual time required at 0.528 template similarity | `- -` | 17 for Tesseract. Built-in reading withheld |

The prototype keeps the built-in reader for this fixed synthetic layout.
Both readers decoded the clear frames, and the built-in confidence
threshold sends the blurry frame to manual entry.

Run `python eval/compare_overlay.py` with local Tesseract and its English
trained data installed to reproduce the comparison. The raw outputs are
in [overlay-comparison.json](overlay-comparison.json).
