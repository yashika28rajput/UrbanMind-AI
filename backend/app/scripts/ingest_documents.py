from __future__ import annotations

import argparse
from pathlib import Path

from app.services.rag_service import rag_service


def _iter_supported_files(directory: Path):
    extensions = {".txt", ".md", ".csv", ".json", ".pdf"}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in extensions:
            yield path


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest urban knowledge documents into the local RAG index.")
    parser.add_argument("--path", type=str, required=True, help="Directory containing documents to index.")
    args = parser.parse_args()

    base = Path(args.path)
    if not base.exists():
        raise FileNotFoundError(f"Path does not exist: {base}")

    documents = list(_iter_supported_files(base))
    if not documents:
        print(f"No supported files found under {base}")
        return
    ingested = 0
    for file_path in documents:
        try:
            rag_service.ingest_file(path=file_path)
            ingested += 1
            print(f"Ingested {file_path.name}")
        except Exception as exc:  # pragma: no cover - CLI diagnostics
            print(f"Failed to ingest {file_path.name}: {exc}")
    print(f"Completed ingestion for {ingested} files.")


if __name__ == "__main__":
    main()
