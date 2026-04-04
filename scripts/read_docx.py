#!/usr/bin/env python3
"""Extract text content from a .docx file. Used by sub-agents during file analysis.

Usage: python3 read_docx.py <path_to_docx> [--max-chars 2000]

Outputs the first N characters of text content (default 2000), which is enough
for a sub-agent to understand what the document is about without loading
the entire thing into context.
"""

import sys
import argparse


def extract_text(path, max_chars=2000):
    try:
        from docx import Document
        doc = Document(path)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        # Fallback: extract from raw XML
        import zipfile
        import re
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        text = " ".join(re.findall(r"<w:t[^>]*>([^<]+)</w:t>", xml))

    if max_chars and len(text) > max_chars:
        text = text[:max_chars] + "\n[... truncated]"
    return text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract text from .docx")
    parser.add_argument("path", help="Path to .docx file")
    parser.add_argument("--max-chars", type=int, default=2000,
                        help="Max characters to output (default: 2000, 0 = unlimited)")
    args = parser.parse_args()
    print(extract_text(args.path, args.max_chars or None))
