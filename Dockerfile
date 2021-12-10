FROM python:3.10.1

LABEL maintainer="openlibrary@archive.org"

ENV DEBIAN_FRONTEND=nonintercative

RUN apt-get update -y && apt-get install -y libpq-dev

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

COPY . /app

WORKDIR /app/bestbook
CMD [ "python3", "app.py" ]
