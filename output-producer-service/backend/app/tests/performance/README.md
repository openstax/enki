Load testing of COPS
====================

Load tests for COPS.

**Warning:** Be very careful before testing any production URLs! Speak with your team before doing so.

## Setup

There is a `docker-compose.loadtests.yml` file which can be used to bring up the load testing environment in a stack configuration. You can simply add the file to your invocation of `docker-compose`, and the configuration will add `locust` and `dnsmasq` services to your environment.

## How to run load tests

[Locust](https://locust.io/) provides a UI that can be used to run backend load tests and view results. The interface can be reached using port `8089` in your browser: [http://localhost:8089](http://localhost:8089)

By default the load test will target the local Docker host service via `http://backend`, but you can modify this URL to target other environments such as staging.

To start a very simple load test set
**users** to `100`
and
**hatch** rate to `10`

Start running the load test and see the result in your browser! :)

## Known issues

* Load testing non-`GET` requests
* Distributed load testing
