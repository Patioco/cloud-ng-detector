# ---- Base image ----
FROM python:3.11-slim

# ---- System dependencies ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    iptables \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Create non-root user ----
RUN useradd -m detector
USER detector

# ---- Set working directory ----
WORKDIR /app

# ---- Copy requirements and install ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy detector source code ----
COPY ./detector .

# ---- Expose dashboard port ----
EXPOSE 8080

# ---- Run the detector ----
CMD ["python", "main.py"]
