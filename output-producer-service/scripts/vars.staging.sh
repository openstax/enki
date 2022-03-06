#!/usr/bin/env bash
export DOMAIN="corgi-staging.openstax.org"
export STACK_NAME="corgi_stag"
export TRAEFIK_TAG="traefik-staging"

NEWLINE=$'\n'
echo "${NEWLINE}The following environment variables were set:${NEWLINE}"
echo "DOMAIN=$DOMAIN"
echo "STACK_NAME=$STACK_NAME"
echo "TRAEFIK_TAG=$TRAEFIK_TAG"
echo "${NEWLINE}"
