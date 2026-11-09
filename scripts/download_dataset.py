"""Download and extract DBpedia-OpenAI-1M (Qdrant's packaged copy) into datasets/raw/.

Produces datasets/raw/vectors.npy and datasets/raw/tests.jsonl; the archive is
deleted after extraction.
"""
import tarfile
import urllib.request
from pathlib import Path

URL = "https://storage.googleapis.com/ann-filtered-benchmark/datasets/dbpedia_openai_1M.tgz"
RAW = Path(__file__).resolve().parent.parent / "datasets" / "raw"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    if (RAW / "vectors.npy").exists() and (RAW / "tests.jsonl").exists():
        print("raw dataset already present, nothing to do")
        return

    archive = RAW / "dbpedia_openai_1M.tgz"
    if not archive.exists():
        print(f"downloading {URL} (~5.1 GB)", flush=True)
        urllib.request.urlretrieve(URL, archive)

    print("extracting", flush=True)
    with tarfile.open(archive) as tar:
        tar.extractall(RAW, filter="data")
    archive.unlink()
    print("done:", sorted(p.name for p in RAW.iterdir()))


if __name__ == "__main__":
    main()
