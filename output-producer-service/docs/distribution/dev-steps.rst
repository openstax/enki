.. _distribution-pipeline-dev-steps:

#########################
Developer Pipeline Set Up
#########################

Internal Development and/or Debugging of Distribution Pipeline Steps
The approach allows developers / QA to inspect all input / output files for tasks
to confirm data is being generated as expected.

Each step of the distribution pipeline can be run individually and step by step.

----

*************
Prerequisites
*************

`Install Docker <https://docs.docker.com/get-docker/>`_
=========================================================

`Install AWS CLI <https://aws.amazon.com/cli/>`_
================================================

Clone output-producer-service
=============================

.. code-block:: bash

    $ git cllone git@github.com:openstax/output-producer-service.git

Install Concourse fly cli
===========================

- For Linux, `Download the cli command binary <https://concourse-ci.org/quick-start.html>`_
- For Mac, Install with ``brew cask install fly``.

Setup AWS resources
===================
The Distribution Pipeline needs to be configured with two S3 buckets, both of which
should be configured with versioning enabled. While it is possible (for development)
to use the same bucket in both configuration settings, it's recommended to have
separate buckets to better represent the `production configuration <https://github.com/openstax/unified-deployment/tree/master/apps/web_hosting_content_s3>`_.

----

*****
Steps
*****

1. Get Concourse Up
===================

**1. Start the whole infrastructure, from root of output-proudcer-service**

.. code-block:: bash

   $ cd output-producer-service
   $ docker-compose up -d

**2. Ensure Concourse is up by visiting** `http://localhost:8100 <http://localhost:8100>`_ **in your browser.**

* login:``dev``
* password: ``dev``

You should see no pipelines running.

-------

2. Define Pipeline Environment Variables
========================================
The Distribution Pipeline is configured using multiple variables in the environment
specific JSON file in ``bakery/env``. Some of these are shared with the PDF pipeline,
while others pertain only to it:

* ``S3_ACCESS_KEY_ID``: AWS credential for S3 access
* ``S3_SECRET_ACCESS_KEY``: AWS credential for S3 access
* ``QUEUE_FILENAME``: A filename to use for the versioned S3 file
* ``WEB_S3_BUCKET``: The S3 bucket where the pipeline should upload content (e.g. JSON and XHTML files)
* ``WEB_QUEUE_STATE_S3_BUCKET``: The S3 bucket where the pipeline will create files of two forms:

    * ``<code version>/.<collection_id>@<version>.complete``: These are code version and book specific
      files indicating completion of a build. Their content inludes an ISO-8601 timestamp of when the ``upload-task`` created and uploaded the marker file.
    * ``<code version>.<QUEUE_FILENAME>``: The code version specific instance of a versioned file used
      by the ``feeder`` and ``bakery`` jobs.

* ``DIST_FEED_FILE_URL``: The URL for the input JSON feed
* ``PIPELINE_TICK_INTERVAL``: A string that represents the interval for the periodic tick.
  This should be compatible with the format accepted by the `Concourse time resource <https://github.com/concourse/time-resource#source-configuration>`_.
  (examples: ``30m``, ``1h``, ...)
* ``MAX_BOOKS_PER_TICK``: The maximum number of books to queue in a single invocation of
  the ``check-feed`` task in the ``feeder`` job.

.. important::
    The value of ``QUEUE_FILENAME`` should be selected such that the file ``<code version>.<QUEUE_FILENAME>`` in
    ``WEB_QUEUE_STATE_S3_BUCKET`` has never existed prior to the pipeline being created. The reason being otherwise even "deleting"
    a file will cause Concourse to see a version preceding the delete, and it will pick it up as a
    job. In production this will be less of a  concern since only pipelines will write to the environment.
    However, for development you can adopt a convention such as ``web-hosting-queue-<your initials>-<nonce>.json``
    so as you iterate testing within a code version you can maintain a unique filename (you only need the initials if
    the bucket you use in AWS is shared by multiple users for dev / QA).

An example of ``local.json`` settings for a developer might look like the following (which assumes you're using
S3 to host your feed file):

.. code-block:: json

    {
        "ENV_NAME": "local",
        "COPS_TARGET": "http://backend/api",
        "COPS_ARTIFACTS_S3_BUCKET": "artifacts-bucket",
        "S3_ACCESS_KEY_ID": "MODIFY ME",
        "S3_SECRET_ACCESS_KEY": "MODIFY_ME",
        "WEB_QUEUE_STATE_S3_BUCKET": "ce-rap-dev-dist2",
        "QUEUE_FILENAME": "web-hosting-queue-abc-1.json",
        "DIST_FEED_FILE_URL": "https://ce-rap-dev-dist2.s3.amazonaws.com/distribution-feed.json",
        "PIPELINE_TICK_INTERVAL": "20m",
        "MAX_BOOKS_PER_TICK": "3"
    }

3. Create and Upload Feed File
==============================
The feed file you use determines the list of books built by the pipeline. An example
might be:

.. code-block:: json

    [
        {"collection_id": "col30149", "server": "staging.cnx.org", "style": "business-ethics", "version": "1.8"},
        {"collection_id": "col30149", "server": "staging.cnx.org", "style": "business-ethics", "version": "1.7"},
        {"collection_id": "col30149", "server": "staging.cnx.org", "style": "business-ethics", "version": "1.6"},
        {"collection_id": "col30149", "server": "staging.cnx.org", "style": "business-ethics", "version": "1.5"}
    ]

You can test your feed file with the schema using something like the following
(which assumes you have ``content-manager-approved-books`` checked out locally and ``jsonschema``
installed in your virtual environment)

.. code-block:: bash

    jsonschema -i distribution-feed.json content-manager-approved-books/schema.json

When using S3 to host your ``distribution-feed.json`` file, you can upload with the
CLI and set the appropriate ACLs as follows:

.. code-block:: bash

    aws s3 cp distribution-feed.json s3://ce-rap-dev-dist2/distribution-feed.json --acl public-read

4. Set Concourse Pipeline
=========================

**1. Target the Concourse Fly Cli to the Concourse server:**

Run ``fly targets``. If you don't see `http://localhost:8100` listed under url, run:

.. code-block:: bash

   fly -t corgi-dev login -c http://localhost:8100 -u dev -p dev

We've named this target ``corgi-dev``.

.. note::
   Production Concourse Target URL: https://concourse-dev0.openstax.org

**2. Set the pipeline with a name and configurations.**

Must have a configuration file to run the following: :ref:`operations-generate-pipeline-config`.

.. code-block:: bash

    $ cd bakery
    $ fly -t corgi-dev sp -p distribution -c distribution-pipeline.local.yml

We've named this pipeline ``distribution`` and passed in config file ``distribution-pipeline.local.yml``.

..  warning::

    **Invalid Token Warning**

    .. code-block:: bash

        could not find a valid token.
        logging in to team 'main'

        navigate to the following URL in your browser:

            http://localhost:8100/login?fly_port=57012

    | If navigating to the URL does not work, try:
    | ``ctrl+c`` and  ``fly -t corgi-dev login -c http://localhost:8100 -u dev -p dev``

    **Version Mismatch Warning**

    If a mismatch occurs between the **fly cli version** and **Concourse version**
    this can be fixed with the ``fly -t <target_name> sync`` command.



**3. Confirm Pipeline Configurations.**

.. code-block:: bash

    apply configuration? [yN]: y
    pipeline created!

**4. Unpause Pipeline**

.. code-block:: bash

   fly -t corgi-dev unpause-pipeline -p distribution

The Distribution pipeline has now been set up to process jobs.

-------

5. Watch Pipeline Work
======================

You can view the Pipeline in your `local Concourse <http://localhost:8100>`_ .
You will notice that both jobs should fire up shortly after you unpause. The
``bakery`` pipeline will fire the first time with a dummy ``initializing``
``version_id``. You should observe it fail during ``dequeue book`` with a
message similar to the following:

.. code-block:: bash

    + exec
    Book is empty

Depending upon your specific settings, you will see the feeder task queue some
number of books. Following the examples above, you would see output similar to
the following in the ``check feed`` task:

.. code-block:: bash

    + curl https://ce-rap-dev-dist2.s3.amazonaws.com/distribution-feed.json -o book-feed.json
    % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                    Dload  Upload   Total   Spent    Left  Speed
    100   435  100   435    0     0   1694      0 --:--:-- --:--:-- --:--:--  1699
    + python /code/scripts/check-feed.py book-feed.json 20200618.170657 ce-rap-dev-dist2 20200618.170657.distribution-queue-abc-1.json 3
    Checking for s3://ce-rap-dev-dist2/20200618.170657/.col30149@1.8.complete
    Found feed entry to build: {'collection_id': 'col30149', 'server': 'staging.cnx.org', 'style': 'business-ethics', 'version': '1.8'}
    Checking for s3://ce-rap-dev-dist2/20200618.170657/.col30149@1.7.complete
    Found feed entry to build: {'collection_id': 'col30149', 'server': 'staging.cnx.org', 'style': 'business-ethics', 'version': '1.7'}
    Checking for s3://ce-rap-dev-dist2/20200618.170657/.col30149@1.6.complete
    Found feed entry to build: {'collection_id': 'col30149', 'server': 'staging.cnx.org', 'style': 'business-ethics', 'version': '1.6'}
    Queued 3 books

You'll also see a filename similar to ``20200618.170657.distribution-queue-abc-1.json``
show up in the ``ce-rap-dev-dist2`` bucket:

.. code-block:: bash

    aws s3 ls s3://ce-rap-dev-dist2
    2020-06-18 16:28:28        104 20200618.170657.distribution-queue-abc-1.json
    2020-06-18 16:28:08        435 distribution-feed.json

After a bit, the ``bakery`` job will
pick up those 3 books as concurrent jobs. Once those complete successfully, you
will find content in the ``ce-rap-dev-dist1`` bucket and ``.complete`` files in
``ce-rap-dev-dist2``:

.. code-block:: bash

    aws s3 ls --recursive s3://ce-rap-dev-dist2
    2020-06-18 16:28:28        104 20200618.170657.distribution-queue-abc-1.json
    2020-06-18 16:36:36         26 20200618.170657/.col30149@1.6.complete
    2020-06-18 16:36:37         26 20200618.170657/.col30149@1.7.complete
    2020-06-18 16:36:37         26 20200618.170657/.col30149@1.8.complete
    2020-06-18 16:28:08        435 distribution-feed.json

    aws s3 ls --recursive s3://ce-rap-dev-dist1
    2020-06-18 16:35:37      54597 apps/archive/20200618.170657/contents/464a3fba-68c1-426a-99f9-597e739dc911@6.6.json
    2020-06-18 16:35:42      31246 apps/archive/20200618.170657/contents/464a3fba-68c1-426a-99f9-597e739dc911@6.6.xhtml
    ...

In subsequent "ticks", the pipeline will build additional books until the feed is
completely processed.
