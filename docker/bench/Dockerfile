# Benchmark client: VectorDBBench + data-preparation tooling.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt /tmp/requirements.txt
# gcc is only needed to build hdrhistogram (no aarch64 wheel); removed afterwards.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libc6-dev \
 && pip install -r /tmp/requirements.txt \
 && apt-get purge -y gcc libc6-dev && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work
CMD ["vectordbbench", "--help"]
