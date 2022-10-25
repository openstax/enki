FROM openstax/python3-poetry as concourse-resource-builder

WORKDIR /code
COPY . .

RUN poetry build -f sdist

###

FROM openstax/python3-base as resource-runner

WORKDIR /tmp
COPY --from=concourse-resource-builder /code/dist .
RUN set -x \
    && pip3 install corgi-concourse-resource-*.tar.gz \
    && mkdir -p /opt/resource \
    && for script in check in out; do ln -s $(which $script) /opt/resource/; done
