FROM alpine:latest

LABEL maintainer="OpenStax Content Engineering"

RUN apk --no-cache add dnsmasq
VOLUME /etc/dnsmasq
EXPOSE 53 53/udp

ENTRYPOINT ["dnsmasq", "-k"]
