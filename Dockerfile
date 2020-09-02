FROM ubuntu:16.04

MAINTAINER openlibrary "openlibrary@archive.org"

RUN apt-get update -y && \
    apt-get install -y python-pip python-dev postgresql postgresql-server-dev-9.5

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

ENTRYPOINT [ "python" ]

CMD [ "app.py" ]
