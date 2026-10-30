# IA AISSA — l'application Streamlit, prête pour un serveur à vous.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# libglib2.0-0 : OpenCV (visages) ; libgomp1 : PyTorch et Whisper sur CPU
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY controle_gestion_ia.py montage.py ./
COPY ia_aissa ./ia_aissa
COPY .streamlit ./.streamlit
COPY exemples ./exemples

RUN useradd --create-home aissa && chown -R aissa /app
USER aissa
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD curl -fs http://localhost:8501/_stcore/health || exit 1
CMD ["streamlit", "run", "controle_gestion_ia.py", "--server.address=0.0.0.0", "--server.port=8501", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
