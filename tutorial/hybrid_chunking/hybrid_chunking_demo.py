import argparse
import logging
from pathlib import Path
from typing import Iterable, Optional


def _build_logger() -> logging.Logger:
	logger = logging.getLogger("hybrid_chunking_demo")
	if not logger.handlers:
		handler = logging.StreamHandler()
		formatter = logging.Formatter(
			"%(asctime)s | %(levelname)s | %(name)s | %(message)s"
		)
		handler.setFormatter(formatter)
		logger.addHandler(handler)
	logger.setLevel(logging.INFO)
	return logger


def _load_hf_tokenizer(model_name: Optional[str]):
	if not model_name:
		return None
	try:
		from transformers import AutoTokenizer  # type: ignore
	except Exception as exc:  # pragma: no cover - optional dependency
		raise RuntimeError(
			"transformers is not installed. Install via 'uv pip install transformers' or 'pip install transformers'."
		) from exc
	return AutoTokenizer.from_pretrained(model_name, use_fast=True)


def chunk_document(
	source_path: Path,
	tokenizer_model: Optional[str] = None,
	print_top: int = 5,
) -> None:
	"""Convert a document with Docling and chunk it with HybridChunker.

	Args:
		source_path: Path to the input document (markdown, pdf, etc.).
		tokenizer_model: Optional HF tokenizer model name for alignment with embedding model.
		print_top: Number of chunks to print as preview.
	"""
	logger = _build_logger()
	if not source_path.exists():
		raise FileNotFoundError(f"Input not found: {source_path}")

	from docling.document_converter import DocumentConverter  # type: ignore
	from docling.chunking import HybridChunker  # type: ignore

	logger.info("Converting document: %s", source_path)
	dl_doc = DocumentConverter().convert(source=str(source_path)).document

	hf_tokenizer = _load_hf_tokenizer(tokenizer_model)
	chunker = HybridChunker(tokenizer=hf_tokenizer) if hf_tokenizer else HybridChunker()

	logger.info("Chunking with HybridChunker (tokenizer=%s)", tokenizer_model or "default")
	chunks: Iterable = chunker.chunk(dl_doc=dl_doc)

	for i, chunk in enumerate(chunks):
		if i >= print_top:
			break
		text = chunk.text or ""
		enriched = chunker.contextualize(chunk=chunk)
		logger.info("=== chunk %d ===", i)
		logger.info("text:\n%s", (text[:500] + ("…" if len(text) > 500 else "")))
		logger.info(
			"contextualized:\n%s",
			(enriched[:500] + ("…" if len(enriched) > 500 else "")),
		)


if __name__ == "__main__":
	default_source = Path(__file__).parent / "data" / "wiki.md"
	parser = argparse.ArgumentParser(description="Docling Hybrid Chunking demo")
	parser.add_argument(
		"--source",
		type=Path,
		default=default_source,
		help=f"Path to input file (default: {default_source})",
	)
	parser.add_argument(
		"--tokenizer",
		type=str,
		default=None,
		help=(
			"HF tokenizer model name to align with embedding model, e.g. "
			"'sentence-transformers/all-MiniLM-L6-v2'"
		),
	)
	parser.add_argument(
		"--print-top",
		type=int,
		default=5,
		help="Number of chunks to print as preview",
	)
	args = parser.parse_args()
	chunk_document(args.source, args.tokenizer, args.print_top)
