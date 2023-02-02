FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE 1 \
    PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y git
RUN pip install --upgrade --no-cache-dir 'black==23.1.0'

COPY entrypoint.sh /entrypoint.sh
COPY main.py /main.py

ENTRYPOINT ["/entrypoint.sh"]
