"""Generate 4 realistic multi-page financial seed PDF documents."""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.infrastructure.document_processing.seed_generator import generate_seed_pdf_files

def main():
    seed_dir = Path(__file__).resolve().parent.parent / "seed_documents"
    print(f"Generating seed PDFs in: {seed_dir}")
    files = generate_seed_pdf_files(seed_dir)
    print(f"Successfully created {len(files)} financial PDF documents:")
    for f in files:
        print(f" - {f.name} ({f.stat().st_size} bytes)")

if __name__ == "__main__":
    main()

