# The JobMatch SE app: FastAPI backend + website, in one container.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models

WORKDIR /app

# 1. PyTorch for CPU only (much smaller than the default GPU version)
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# 2. The other libraries. Only pyproject.toml is copied here, so this slow step
#    is cached by Docker and only runs again when the dependencies change.
COPY pyproject.toml ./
RUN mkdir -p src/jobmatch && touch src/jobmatch/__init__.py && pip install -e .

# 3. The code itself (changes often, so it comes last)
COPY src ./src
COPY web ./web

EXPOSE 8000
CMD ["uvicorn", "jobmatch.api.main:app", "--host", "0.0.0.0", "--port", "8000"]