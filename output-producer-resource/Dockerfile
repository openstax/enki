FROM python:3.7-slim

COPY . /code

WORKDIR /code

RUN python setup.py sdist

RUN pip install dist/output-producer-resource-*.tar.gz
RUN mkdir -p /opt/resource
RUN for script in check in out; do ln -s $(which $script) /opt/resource/; done
