FROM ubuntu:20.04

LABEL maintainer="openlibrary@archive.org"

ENV DEBIAN_FRONTEND=nonintercative

RUN apt-get update -y && \
    apt-get install -y python3-pip python3-dev postgresql postgresql-server-dev-12

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN python3 -m pip install --upgrade pip

RUN python3 -m pip install -r requirements.txt

COPY . /app

ENTRYPOINT [ "python3" ]

CMD [ "bestbook/app.py" ]
