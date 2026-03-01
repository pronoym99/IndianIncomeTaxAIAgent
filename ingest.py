import os, json, hashlib, pickle, argparse
from pathlib import Path
from dotenv import load_dotenv
import numpy as np
from azure_openai import create_client
from typing import Iterable, List, Dict

load_dotenv()

DEFAULT_DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
STORE_DIR = Path(os.environ.get("STORE_DIR", "vector_store"))
STORE_DIR.mkdir(exist_ok=True)
EMB_STORE = STORE_DIR / "embeddings.pkl"

EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
client = create_client()

def flatten(obj, parent="") -> List[str]:
    """Recursively flatten a JSON-like structure into dotted key: value lines."""
    lines: List[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            newp = f"{parent}.{k}" if parent else k
            lines.extend(flatten(v, newp))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            newp = f"{parent}[{i}]"
            lines.extend(flatten(v, newp))
    else:
        lines.append(f"{parent}: {obj}")
    return lines

def chunk_lines(lines: Iterable[str], max_chars=1200, overlap=120) -> Iterable[str]:
    """Yield concatenated text chunks of ~max_chars with character-level overlap."""
    buffer: List[str] = []
    size = 0
    for line in lines:
        if size + len(line) + 1 > max_chars and buffer:
            yield "\n".join(buffer)
            # overlap tail
            overlap_chars = 0
            overlap_buf: List[str] = []
            for bl in reversed(buffer):
                overlap_chars += len(bl)
                overlap_buf.append(bl)
                if overlap_chars > overlap:
                    break
            buffer = list(reversed(overlap_buf))
            size = sum(len(b) for b in buffer)
        buffer.append(line)
        size += len(line)
    if buffer:
        yield "\n".join(buffer)

def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts. Simple sequential loop (hackathon scale)."""
    embeddings: List[List[float]] = []
    for i, t in enumerate(texts):
        resp = client.embeddings.create(model=EMBED_MODEL, input=t)
        embeddings.append(resp.data[0].embedding)
        if (i+1) % 10 == 0:
            print(f"  Embedded {i+1}/{len(texts)}")
    return embeddings

def discover_files(data_dir: Path) -> List[Path]:
    exts = {".json", ".txt", ".md"}
    files = []
    for p in sorted(data_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
    return files

def load_and_chunk(path: Path, max_chars=1200, overlap=120) -> List[str]:
    """Load a file and produce text chunks."""
    try:
        if path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            lines = flatten(data)
        else:  # text / markdown
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            # simple split – keep paragraphs
            paragraphs = [p.strip() for p in content.splitlines() if p.strip()]
            lines = paragraphs
        return list(chunk_lines(lines, max_chars=max_chars, overlap=overlap))
    except Exception as e:
        print(f"Failed to process {path}: {e}")
        return []

def build_arg_parser():
    ap = argparse.ArgumentParser(description="Ingest all data files into local embedding store.")
    ap.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Directory containing source data files (json/txt/md).")
    ap.add_argument("--out", type=Path, default=EMB_STORE, help="Output embeddings pickle path.")
    ap.add_argument("--max-chars", type=int, default=int(os.environ.get("CHUNK_MAX_CHARS", 1200)))
    ap.add_argument("--overlap", type=int, default=int(os.environ.get("CHUNK_OVERLAP", 120)))
    ap.add_argument("--force", action="store_true", help="Overwrite existing embeddings file.")
    return ap

def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    if not EMBED_MODEL:
        raise SystemExit("EMBED_MODEL not set. Deploy an embedding model (e.g. text-embedding-3-small) and set EMBED_MODEL env var.")

    data_dir: Path = args.data_dir
    out_path: Path = args.out

    if out_path.exists() and not args.force:
        print(f"Output {out_path} exists. Use --force to overwrite.")
        return
    if not data_dir.exists():
        raise SystemExit(f"Data directory not found: {data_dir}")

    files = discover_files(data_dir)
    if not files:
        raise SystemExit(f"No supported files found in {data_dir}")
    print(f"Discovered {len(files)} data files.")

    all_chunks: List[Dict] = []
    total_chunks = 0
    for fp in files:
        chunks = load_and_chunk(fp, max_chars=args.max_chars, overlap=args.overlap)
        print(f"  {fp.name}: {len(chunks)} chunks")
        for i, ch in enumerate(chunks):
            all_chunks.append({
                "source": str(fp.relative_to(data_dir)),
                "chunk_index": i,
                "text": ch
            })
        total_chunks += len(chunks)

    print(f"Total chunks: {total_chunks}. Embedding...")
    embeddings = embed_texts([c["text"] for c in all_chunks])

    records = []
    for rec, emb in zip(all_chunks, embeddings):
        uid_seed = f"{rec['source']}:::{rec['chunk_index']}".encode()
        rec_id = hashlib.sha1(uid_seed).hexdigest()
        records.append({
            "id": rec_id,
            "text": rec["text"],
            "embedding": np.array(emb, dtype="float32"),
            "source": rec["source"],
            "chunk_index": rec["chunk_index"],
        })

    with open(out_path, "wb") as f:
        pickle.dump(records, f)
    print(f"Stored {len(records)} chunks in {out_path}")

if __name__ == "__main__":
    main()