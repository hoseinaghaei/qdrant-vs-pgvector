#!/usr/bin/env sh
# Run one VectorDBBench custom-dataset case inside the bench container.
#   usage: scripts/run_vdbb.sh <qdrant|pgvector> <1k|10k|100k|1m> [extra vectordbbench args]
# Both engines get the same HNSW parameters so results are comparable.
set -eu

ENGINE="$1"; SIZE="$2"; shift 2

M="${HNSW_M:-16}"
EF_CONSTRUCTION="${HNSW_EF_CONSTRUCTION:-200}"
EF_SEARCH="${HNSW_EF_SEARCH:-128}"

case "$SIZE" in
  1k)   N=1000 ;;
  10k)  N=10000 ;;
  100k) N=100000 ;;
  1m)   N=975000 ;;
  *) echo "unknown size: $SIZE" >&2; exit 1 ;;
esac

DATASET="dbpedia_openai_${SIZE}"
COMMON="--case-type PerformanceCustomDataset
  --custom-case-name ${DATASET}
  --custom-dataset-name dbpedia_openai
  --custom-dataset-dir /work/datasets/${DATASET}
  --custom-dataset-size ${N}
  --custom-dataset-dim 1536
  --custom-dataset-metric-type COSINE
  --custom-dataset-file-count 1
  --skip-custom-dataset-use-shuffled
  --custom-dataset-with-gt
  --k 100
  --db-label ${ENGINE}-${SIZE}
  --task-label ${ENGINE}-${SIZE}-$(date +%Y%m%d-%H%M%S)"

case "$ENGINE" in
  qdrant)
    # shellcheck disable=SC2086
    exec vectordbbench qdrantlocal $COMMON \
      --url "${QDRANT_URL}" \
      --m "$M" --ef-construct "$EF_CONSTRUCTION" --hnsw-ef "$EF_SEARCH" "$@" ;;
  pgvector)
    # shellcheck disable=SC2086
    exec vectordbbench pgvectorhnsw $COMMON \
      --host "${PG_HOST}" --user-name "${PG_USER}" --password "${PG_PASSWORD}" --db-name "${PG_DB}" \
      --m "$M" --ef-construction "$EF_CONSTRUCTION" --ef-search "$EF_SEARCH" "$@" ;;
  *) echo "unknown engine: $ENGINE" >&2; exit 1 ;;
esac
