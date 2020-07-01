FROM python:3.7-slim

# Needs to exist for jre installation
RUN mkdir -p /usr/share/man/man1/

RUN apt update
RUN apt install -y openjdk-11-jre-headless libmagic1 mime-support

COPY requirements /tmp/requirements

# Install Python Dependencies
RUN set -x \
    && pip install -U pip setuptools wheel \
    && pip install -r /tmp/requirements/lint.txt \
                   -r /tmp/requirements/test.txt \
                   -r /tmp/requirements/main.txt

# Copy the project into the container
COPY . /app/

# Set the working directory for our app
WORKDIR /app/

# Install neb
RUN pip install -e .

