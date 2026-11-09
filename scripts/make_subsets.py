"""Cut nested 1K / 10K / 100K / 975K subsets out of DBpedia-OpenAI-1M and
compute exact ground truth for each, in VectorDBBench custom-dataset format.

Input  (datasets/raw/):  vectors.npy (975000 x 1536 float32), tests.jsonl
Output (datasets/<name>/): train.parquet, test.parquet, neighbors.parquet,
                           orig_ids.npy (new id -> row in vectors.npy)
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "datasets" / "raw"
OUT = ROOT / "datasets"

SIZES = {"dbpedia_openai_1k": 1_000, "dbpedia_openai_10k": 10_000,
         "dbpedia_openai_100k": 100_000, "dbpedia_openai_1m": 975_000}
N_QUERIES = 1_000
K = 100
SEED = 42
CHUNK = 50_000


def emb_array(mat):
    """(n, d) float32 matrix -> Arrow list<float32> column."""
    n, d = mat.shape
    offsets = pa.array(np.arange(0, (n + 1) * d, d, dtype=np.int32))
    return pa.ListArray.from_arrays(offsets, pa.array(mat.reshape(-1)))


def write_vectors(path, vectors, rows):
    """Write vectors[rows] as (id, emb) with id = 0..n-1, chunk by chunk."""
    schema = pa.schema([("id", pa.int64()), ("emb", pa.list_(pa.float32()))])
    with pq.ParquetWriter(path, schema) as w:
        for start in range(0, len(rows), CHUNK):
            block = np.ascontiguousarray(vectors[rows[start:start + CHUNK]])
            ids = pa.array(np.arange(start, start + len(block), dtype=np.int64))
            w.write_table(pa.table({"id": ids, "emb": emb_array(block)}, schema=schema))


def ground_truth(queries, vectors, rows):
    """Exact top-K by inner product (vectors are unit-norm, so = cosine)."""
    best_s = np.full((len(queries), K), -np.inf, dtype=np.float32)
    best_i = np.zeros((len(queries), K), dtype=np.int64)
    for start in range(0, len(rows), CHUNK):
        block = np.ascontiguousarray(vectors[rows[start:start + CHUNK]])
        s = queries @ block.T
        i = np.broadcast_to(np.arange(start, start + len(block)), s.shape)
        s = np.concatenate([best_s, s], axis=1)
        i = np.concatenate([best_i, i], axis=1)
        top = np.argpartition(-s, K - 1, axis=1)[:, :K] if s.shape[1] > K else np.argsort(-s, axis=1)
        best_s = np.take_along_axis(s, top, axis=1)
        best_i = np.take_along_axis(i, top, axis=1)
    order = np.argsort(-best_s, axis=1)
    return np.take_along_axis(best_i, order, axis=1)


def main():
    vectors = np.load(RAW / "vectors.npy", mmap_mode="r")
    total = vectors.shape[0]

    tests = []
    with open(RAW / "tests.jsonl") as f:
        for line in f:
            tests.append(json.loads(line))
            if len(tests) == N_QUERIES:
                break
    queries = np.array([t["query"] for t in tests], dtype=np.float32)
    given_top10 = np.array([t["closest_ids"] for t in tests])

    # One random permutation; every subset is a prefix of it, so 1K ⊂ 10K ⊂ 100K ⊂ 975K.
    perm = np.random.default_rng(SEED).permutation(total)

    for name, size in SIZES.items():
        t0 = time.time()
        rows = np.sort(perm[:size])  # sorted -> sequential reads from the mmap
        d = OUT / name
        d.mkdir(parents=True, exist_ok=True)

        write_vectors(d / "train.parquet", vectors, rows)
        pq.write_table(pa.table({"id": pa.array(np.arange(len(queries), dtype=np.int64)),
                                 "emb": emb_array(queries)}), d / "test.parquet")
        gt = ground_truth(queries, vectors, rows)
        pq.write_table(pa.table({"id": pa.array(np.arange(len(queries), dtype=np.int64)),
                                 "neighbors_id": pa.array(list(gt), type=pa.list_(pa.int64()))}),
                       d / "neighbors.parquet")
        np.save(d / "orig_ids.npy", rows)

        msg = f"{name}: {size} vectors, {len(queries)} queries, top-{K} GT in {time.time() - t0:.1f}s"
        if size == total:
            # Check our ground truth against the one shipped with the dataset.
            ours = rows[gt[:, :10]]
            match = np.mean([len(set(a) & set(b)) / 10 for a, b in zip(ours, given_top10)])
            msg += f" | top-10 agreement with shipped GT: {match:.4f}"
        print(msg, flush=True)


if __name__ == "__main__":
    sys.exit(main())
