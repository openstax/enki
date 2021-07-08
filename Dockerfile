# syntax = edrevo/dockerfile-plus

INCLUDE+ Dockerfile.common

WORKDIR /data/

RUN useradd --create-home -u 5000 app

ENV RUN_AS="app:app"
ENV ORIG_ENTRYPOINT='/dockerfiles/docker-entrypoint-with-kcov.sh'
ENTRYPOINT ["/dockerfiles/entrypointd.sh"]
HEALTHCHECK CMD /dockerfiles/healthcheckd.sh
