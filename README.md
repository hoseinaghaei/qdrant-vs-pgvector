# Qdrant vs pgvector — Vector DBMS Benchmark

Advanced Databases course project. We compare two vector database systems on the same workload:

- **Qdrant**: a database built specifically for vector search
- **pgvector**: a PostgreSQL extension that adds vector search to a relational database

The goal is to measure how each one scales from 1K to ~1M vectors (linear or worse?) and whether it holds up at full size.

## Benchmark method

- **Tool:** [VectorDBBench](https://github.com/zilliztech/VectorDBBench), an open-source benchmark that supports both a local Qdrant and pgvector. Results are cross-checked with [qdrant/vector-db-benchmark](https://github.com/qdrant/vector-db-benchmark).
- **Dataset:** [DBpedia entities × OpenAI `text-embedding-ada-002`](https://huggingface.co/datasets/KShivendu/dbpedia-entities-openai-1M): 1536 dimensions, cosine distance, real embeddings (nothing generated). We use Qdrant's packaged copy: <https://storage.googleapis.com/ann-filtered-benchmark/datasets/dbpedia_openai_1M.tgz> (975,000 vectors plus 5,000 separate test queries).
- **Repetitions:** each query/update workload runs 6 times. The first run fills the caches and is discarded, and the remaining 5 are averaged.
- **Metrics:** QPS, recall@k, p99 latency, load time and index build time.

## Dataset subsets

`scripts/make_subsets.py` shuffles the 975K vectors once (seed 42) and takes prefixes of that order, so the subsets are nested and only the size changes:

| Name | Vectors | Queries | Ground truth |
|---|---|---|---|
| `dbpedia_openai_1k` | 1,000 | 1,000 | exact top-100 |
| `dbpedia_openai_10k` | 10,000 | 1,000 | exact top-100 |
| `dbpedia_openai_100k` | 100,000 | 1,000 | exact top-100 |
| `dbpedia_openai_1m` | 975,000 | 1,000 | exact top-100 |

- **Ground truth:** computed exactly by brute force for each subset (vectors are unit-norm, so inner product = cosine). At 975K it agrees 100% with the top-10 shipped with the dataset (`logs/make_subsets.log`).
- **Output format:** each folder follows VectorDBBench's custom-dataset format: `train.parquet` (`id`, `emb`), `test.parquet` (`id`, `emb`), `neighbors.parquet` (`id`, `neighbors_id`), plus `orig_ids.npy`, which maps each new id to its row in the original `vectors.npy`.

## Reproduce

```bash
# 1. Environment (Python >= 3.11, required by VectorDBBench)
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt

# 2. Download and extract the raw dataset (~5.1 GB compressed, ~6.2 GB extracted)
mkdir -p datasets/raw
curl -L -o datasets/raw/dbpedia_openai_1M.tgz \
  https://storage.googleapis.com/ann-filtered-benchmark/datasets/dbpedia_openai_1M.tgz
tar -xzf datasets/raw/dbpedia_openai_1M.tgz -C datasets/raw

# 3. Build the subsets and ground truth (~2 min on an Apple M1)
.venv/bin/python scripts/make_subsets.py
```

The `datasets/` folder is git-ignored: it is several GB and fully re-creatable with the steps above.

## Repository layout

```
scripts/     data preparation and benchmark scripts
logs/        run logs kept for the report
datasets/    raw data and generated subsets (git-ignored)
```
