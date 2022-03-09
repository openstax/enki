FROM python:3.7-slim

LABEL maintainer="OpenStax Content Engineering"

RUN apt-get update && apt-get install -y build-essential libicu-dev pkg-config libmagic1 \
    mime-support wget curl xsltproc lsb-release git \
    imagemagick icc-profiles-free curl unzip

COPY ./requirements.txt /code/scripts/
WORKDIR /code/

RUN pip install -r scripts/requirements.txt

ENV JQ_VERSION='1.6'
ENV PANDOC_VERSION='2.11.3.2'

RUN wget --no-check-certificate https://raw.githubusercontent.com/stedolan/jq/master/sig/jq-release.key -O /tmp/jq-release.key && \
    wget --no-check-certificate https://raw.githubusercontent.com/stedolan/jq/master/sig/v${JQ_VERSION}/jq-linux64.asc -O /tmp/jq-linux64.asc && \
    wget --no-check-certificate https://github.com/stedolan/jq/releases/download/jq-${JQ_VERSION}/jq-linux64 -O /tmp/jq-linux64 && \
    gpg --import /tmp/jq-release.key && \
    gpg --verify /tmp/jq-linux64.asc /tmp/jq-linux64 && \
    cp /tmp/jq-linux64 /usr/bin/jq && \
    chmod +x /usr/bin/jq && \
    rm -f /tmp/jq-release.key && \
    rm -f /tmp/jq-linux64.asc && \
    rm -f /tmp/jq-linux64

RUN wget https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-1-amd64.deb -O /tmp/pandoc.deb && \
    dpkg -i /tmp/pandoc.deb && \
    rm -f /tmp/pandoc.deb

RUN curl -sL https://deb.nodesource.com/setup_14.x | bash -
RUN apt-get install -y nodejs
RUN npm install pm2@4.5.0 -g

COPY ./*.py ./*.js ./*.json /code/scripts/
COPY ./gdoc/ /code/gdoc/

RUN pip install /code/scripts/.
RUN npm --prefix /code/scripts install /code/scripts