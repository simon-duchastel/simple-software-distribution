FROM python:3.11-slim-bookworm

# Install system dependencies required by fdroidserver, apksigner, and nginx.
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jdk-headless \
    apksigner \
    git \
    nginx \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

# Install the F-Droid server tools.
RUN pip install --no-cache-dir fdroidserver

# Copy runtime assets.
COPY generate_site.py /app/generate_site.py
COPY style.css /app/style.css
COPY nginx.conf /app/nginx.conf
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/app/entrypoint.sh"]
