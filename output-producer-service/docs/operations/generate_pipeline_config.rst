.. _operations-generate-pipeline-config:

################################
Generate Pipeline Configurations
################################

*************
Prerequisites
*************

1. `Install Docker <https://docs.docker.com/get-docker/>`_
==========================================================

2. Clone copy of output-producer-service
========================================

.. code-block:: bash

    $ git clone git@github.com:openstax/output-producer-service.git

3. Install Concourse fly cli
============================

- For Linux, `Download the cli command binary <https://concourse-ci.org/quick-start.html>`_
- For Mac, Install with ``brew cask install fly``.

[There is better way to do this with CLI now]

----

***************************
Generate Configuration File
***************************

When running locally, you need to set appropriate AWS credentials in your environment if you don't have them set already:

.. code-block:: bash

    $ export AWS_ACCESS_KEY_ID="VALUE"
    $ export AWS_SECRET_ACCESS_KEY="VALUE"

Generate pipeline configuration file with output flag ``-o``. If no output file is given it will stdout.

.. code-block:: bash

    $ cd bakery
    $ ./build pipeline distribution local -o distribution-pipeline.local.yml

For command usage:

.. code-block:: bash

    $ ./build pipeline -help

This generated file will be used to configure the Concourse pipeline, with the ``set-pipeline`` command.

**Complete steps to set up pipelines:**

- :ref:`pdf-pipeline-steps`
- :ref:`distribution-pipeline-steps`

----

******************************
Generate Task Definition Files
******************************

1. Install Necessary Packages
=============================

.. code-block:: bash

    $ cd bakery
    $ yarn

2. Build ``yml`` Task Definition Files
======================================

.. code-block:: bash

   $ ./build task look-up-feed > look-up-feed.yml
   $ ./build task fetch-book > fetch-book.yml
   $ ./build task assemble-book > assemble-book.yml
   $ ./build task assemble-book-metadata > assemble-book-metadata.yml
   $ ./build task bake-book > bake-book.yml
   $ ./build task bake-book-metadata > bake-book-metadata.yml
   $ ./build task checksum-book > checksum-book.yml
   $ ./build task disassemble-book > disassemble-book.yml
   $ ./build task jsonify-book > jsonify-book.yml

3. Execute Tasks with Task Definitions
======================================

.. code-block:: bash

    $ fly -t corgi-dev execute -c look-up-feed.yml -j ce-corgi-dist-staging/bakery -o book=./data/book
    $ fly -t corgi-dev execute -c fetch-book.yml -j ce-corgi-dist-staging/bakery -i book=./data/book -o fetched-book=./data/fetched-book
    $ fly -t corgi-dev execute -c assemble-book.yml -j ce-corgi-dist-staging/bakery -i book=./data/book -i fetched-book=./data/fetched-book -o assembled-book=./data/assembled-book
    $ fly -t corgi-dev execute -c assemble-book-metadata.yml -j ce-corgi-dist-staging/bakery -i book=./data/book -i assembled-book=./data/assembled-book -o assembled-book-metadata=./data/assembled-book-metadata
    $ fly -t corgi-dev execute -c bake-book.yml -j ce-corgi-dist-staging/bakery -i book=./data/book -i assembled-book=./data/assembled-book -o baked-book=./data/baked-book
    $ fly -t corgi-dev execute -c bake-book-metadata.yml -j ce-corgi-dist-staging/bakery -i book=./data/book -i assembled-book-metadata=./data/assembled-book-metadata -o baked-book-metadata=./data/baked-book-metadata
    $ fly -t corgi-dev execute -c mathify-book.yml -j ce-corgi-dist-staging/bakery -i book=./data/book -i baked-book=./data/baked-book -o mathified-book=./data/mathified-book
    $ fly -t corgi-dev execute -c disassemble-book.yml -j ce-corgi-dist-staging/bakery -i book=./data/book -i baked-book=./data/baked-book -i baked-book-metadata=./data/baked-book-metadata -o disassembled-book=./data/disassembled-book
    $ fly -t corgi-dev execute -c jsonify-book.yml -j ce-corgi-dist-staging/bakery -i book=./data/book -i disassembled-book=./data/disassembled-book -o jsonified-book=./data/jsonified-book
