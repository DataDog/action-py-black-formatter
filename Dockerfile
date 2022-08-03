FROM python:3.8

ENV PYTHONDONTWRITEBYTECODE 1 \
    PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y git
RUN pip install --upgrade --no-cache-dir 'black==19.10b0' 'click==7.1.2'

COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
