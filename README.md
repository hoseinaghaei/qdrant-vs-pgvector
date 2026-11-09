# Qdrant vs pgvector — Vector DBMS Benchmark

Advanced Databases course project. We compare two vector database systems on the same workload:

- **Qdrant**: a database built specifically for vector search
- **pgvector**: a PostgreSQL extension that adds vector search to a relational database

The goal is to measure how each one scales from 1K to ~1M vectors (linear or worse?) and whether it holds up at full size.

**Everything runs in Docker.** Nothing is installed on the host apart from Docker itself.

## Benchmark method

- **Tool:** [VectorDBBench](https://github.com/zilliztech/VectorDBBench) 2.0.0, an open-source benchmark that supports both a local Qdrant and pgvector. Results are cross-checked with [qdrant/vector-db-benchmark](https://github.com/qdrant/vector-db-benchmark).
- **Dataset:** [DBpedia entities × OpenAI `text-embedding-ada-002`](https://huggingface.co/datasets/KShivendu/dbpedia-entities-openai-1M): 1536 dimensions, cosine distance, real embeddings (nothing generated). We use Qdrant's packaged copy: <https://storage.googleapis.com/ann-filtered-benchmark/datasets/dbpedia_openai_1M.tgz> (975,000 vectors plus 5,000 separate test queries).
- **Repetitions:** each query/update workload runs 6 times. The first run fills the caches and is discarded, and the remaining 5 are averaged.
- **Metrics:** QPS, recall@100, p50/p95/p99 latency, load time and index build time.
- **Same index settings for both engines:** HNSW with `m=16`, `ef_construction=200` and `ef_search=128` (override with the `HNSW_M`, `HNSW_EF_CONSTRUCTION` and `HNSW_EF_SEARCH` environment variables).

## Docker setup

| File | What it runs |
|---|---|
| `docker-compose.qdrant.yml` | `qdrant/qdrant:v1.20.0` plus the `bench` client |
| `docker-compose.pgvector.yml` | `pgvector/pgvector:0.8.7-pg18` (PostgreSQL 18) plus the `bench` client |
| `docker/bench.yml` | Shared `bench` service, extended by both compose files |
| `docker/bench/Dockerfile` | Python 3.12 image with VectorDBBench and the data-preparation tools |
| `docker/pgvector/init.sql` | Runs `CREATE EXTENSION vector` on first start |

**Resource limits**
- The database containers are limited equally: `DB_CPUS=4` and `DB_MEMORY=8g` by default.
- The benchmark client gets `BENCH_CPUS=4` and `BENCH_MEMORY=4g`.
- Every limit can be overridden with an environment variable or a `.env` file.

**Running**
- Run one database stack at a time, so the two never compete for the machine.
- Database storage lives in named Docker volumes (`qdrant_storage`, `pgvector_data`).
- The repository is mounted at `/work` in the `bench` container, so datasets, results and logs end up in this folder.

**PostgreSQL tuning for the 8 GB limit** (set in `docker-compose.pgvector.yml`)
- `shared_buffers=2GB`
- `effective_cache_size=6GB`
- `maintenance_work_mem=2GB`, so HNSW index builds stay in memory
- 3 parallel maintenance workers

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
# Short aliases for the two stacks
QD="docker compose -f docker-compose.qdrant.yml"
PG="docker compose -f docker-compose.pgvector.yml"

# 1. Build the benchmark image
$QD build bench

# 2. Download the raw dataset (~5.1 GB) and build the subsets + ground truth (~2 min on an M1)
$QD run --rm --no-deps bench python scripts/download_dataset.py
$QD run --rm --no-deps bench python scripts/make_subsets.py

# 3. Benchmark Qdrant (sizes: 1k | 10k | 100k | 1m)
$QD up -d qdrant
$QD run --rm bench scripts/run_vdbb.sh qdrant 1k
$QD down

# 4. Benchmark pgvector
$PG up -d pgvector
$PG run --rm bench scripts/run_vdbb.sh pgvector 1k
$PG down

# Wipe the database volumes as well: add -v to `down`
```

- **Arguments:** anything after the size is passed straight to VectorDBBench, e.g. `--num-concurrency 1,5,10 --concurrency-duration 30`.
- **Results:** each run writes a JSON file to `results/<Engine>/`.
- **Git:** `datasets/` is git-ignored because it is several GB and fully re-creatable with step 2.

## Repository layout

```
docker-compose.qdrant.yml    Qdrant stack
docker-compose.pgvector.yml  PostgreSQL + pgvector stack
docker/                      bench image, shared bench service, Postgres init
scripts/                     download, subset creation, benchmark runner
results/                     VectorDBBench result JSONs
logs/                        run logs kept for the report
datasets/                    raw data and generated subsets (git-ignored)
```
