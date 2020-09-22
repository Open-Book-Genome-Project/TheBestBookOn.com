FROM ubuntu:20.04

MAINTAINER openlibrary "openlibrary@archive.org"

RUN apt-get update -y && \
    apt-get install -y python3-pip python3-dev postgresql postgresql-server-dev-9.5

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY . /app

ENTRYPOINT [ "python3" ]

CMD [ "app.py" ]
