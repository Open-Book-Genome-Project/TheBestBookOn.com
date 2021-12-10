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

# create psql user
RUN service postgresql start
RUN psql -h 0.0.0.0 -p 5432 -U postgres -d database_name -c "create user bestbook with password '$PSQL_PASSWD' login createdb;"
RUN psql -h 0.0.0.0 -p 5432 -U postgres -d database_name -c "create database bestbooks owner bestbook;"

# create tables via sqlalchemy
RUN python -c 'import api;api.core.Base.metadata.create_all(api.engine)'

CMD [ "bestbook/app.py" ]
