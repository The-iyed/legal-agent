#!/usr/bin/env python3
import os
import sys
import asyncio
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.document_processor.pdf_splitter import PDFSplitterService

async def main():
    test_file = "tests/data/valid_claim.pdf"
    if not os.path.exists(test_file):
        print(f"❌ Missing: {test_file}")
        return
    with open(test_file, "rb") as f:
        content = f.read()
    svc = PDFSplitterService()
    start = time.time()
    result = await svc.analyze_full_document_layout(content, "valid_claim.pdf")
    elapsed = time.time() - start
    if not result.get("success"):
        print(f"❌ Single-pass extraction failed: {result.get('error')}")
        return
    print(f"✅ Single-pass extraction OK in {elapsed:.2f}s")
    print(f"   Pages: {result.get('total_pages')}  Text len: {len(result.get('extracted_text',''))}")
    pages = result.get('page_results', [])
    if pages:
        first = pages[0]
        print(f"   Page 1 length: {len(first.get('extracted_text',''))}")

if __name__ == "__main__":
    asyncio.run(main()) 