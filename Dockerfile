ARG PYTHON_VERSION
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY craw_real_times/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY craw_real_times /app/craw_real_times

CMD ["python", "-m", "craw_real_times"]
