FROM python:3.13.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 DIRECCION_ESCUCHA=0.0.0.0
WORKDIR /demo
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY cliente_control.py cliente_autorizado.py ./
RUN useradd --uid 10001 --create-home ponente
USER 10001
EXPOSE 18473 18524
CMD ["python", "-m", "app.main"]
