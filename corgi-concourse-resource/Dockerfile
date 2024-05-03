FROM openstax/python3-poetry as concourse-resource-builder

WORKDIR /code
COPY . /code/

RUN set -x \
    && pip3 install /code/. \
    && mkdir -p /opt/resource \
    && for script in check in out; do ln -s $(which $script) /opt/resource/; done
