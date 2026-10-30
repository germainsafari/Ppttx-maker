FROM python:3.12-slim

# LibreOffice renders slide previews; fonts-* give reasonable fallbacks for Acumin Pro.
# Put Admind's licensed font files (Acumin Pro *.otf) into engine/fonts/ for pixel-accurate previews.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice-impress fonts-dejavu fonts-liberation fonts-noto-core fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fonts/ /usr/local/share/fonts/admind/
RUN fc-cache -f >/dev/null

COPY app/ app/
COPY templates/ templates/
COPY assets/ assets/

ENV DATA_DIR=/data PYTHONUNBUFFERED=1
VOLUME /data
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8090/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090", "--proxy-headers", "--forwarded-allow-ips=*"]
