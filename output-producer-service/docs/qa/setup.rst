.. _qa-testing-set-up:

################################
Local QA Environment Setup (WIP)
################################

*********
Objective
*********

Get familiar with Concourse by setting up the bakery-pipeline locally.
This is the pipeline which is used under the hood for `Content Output Review and Generation Interface (CORGI) <https://corgi.openstax.org/>`_

*****
Steps
*****

Generate a pipeline configuration file
======================================

There is a bakery directory with a ``pipeline.local.yml`` which can be used to configure your local Concourse. 
Alternatively, if you want to customize some settings (e.g. provide AWS credentials), you can update the corresponding settings in ``bakery/env/local.json`` and generate an updated pipeline configuration:

.. code-block:: bash

   $ cd bakery
   $ ./build pipeline local > pipeline.local.yml

More details on generating pipeline configurations can be found in ``bakery/README.md``

Once generated, you can use the environment specific configuration file as your ``pipeline.yml`` in the subsequent steps.

Setup local concourse server
----------------------------

0. Prerequisites:

- `Docker <https://www.docker.com/>`_

- `fly CLI - Concourse command line tool <https://concourse-ci.org/fly.html>`_

- `wget <https://www.gnu.org/software/wget/>`_

Steps to install wget (as per INSTALL document in the directory):

- download wget-1.20.3.tar.gz (or latest)

- unzip and cd into wget directory

- run brew install gnutls

- run ./configure

- run make

- run make install

- run make clean

1. Retrieve the docker-compose file to set up concourse server locally.
In the /bakery directory that contains your pipeline.yml, run:

.. code-block:: bash

   $ wget https://concourse-ci.org/docker-compose.yml

2. Start your Concourse server locally:

.. code-block:: bash

   $ docker-compose up -d

   Terminal output should show the following:
   Creating network "bakery_default" with the default driver
   Creating bakery_concourse-db_1 ... done
   Creating bakery_concourse_1  ... done

3. To see the pipelines in Concourse UI at work, navigate to:

   `localhost:8080 <localhost:8080>`_

Setup pipeline with local Concourse and pipeline.yml
----------------------------------------------------

1. Target the Concourse UI, so you are able to set the pipelines to UI:

.. code-block:: bash

   $ fly -t local-pipeline-stuff login -c http://localhost:8080 -u test -p test

   where local-pipeline-stuff is the pipeline name,
   url is the concourse UI,
   -u and -p is user and password.

If you get a warning about versions being out of sync, run the provided command.

2. Set the pipeline with the pipeline.yml config file:

.. code-block:: bash

   fly -t local-pipeline-stuff set-pipeline -p pdf-producer -c pipeline.yml

You will be prompted to apply configuration? [yN]: y

3. See the pipeline that was set from the command line in the UI by navigating to `localhost:8080 <localhost:8080>`_
and login.

4. You can unpause the pipeline from the UI, after creating a job in `corgi.openstax.org <https://corgi.openstax.org>`_
for the pipeline to grab.

Setting up local pipeline to monitor jobs on production corgi (temporary solution)
---------------------------------------------------------------------------------

1. in a terminal, run:

.. code-block:: bash

   cd .../Projects/concourse-pipelines/bakery

2. in an editor, open pipeline.yml

3. change both instances of api_root: ((pdf-job-queue-url)) to api_root: https://corgi.openstax.org/api

4. also, comment out the following lines:

.. code-block:: bash

   #   type: s3
   #   source:
   #     bucket: ce-pdf-spike
   #     access_key_id: ((aws-sandbox-secret-key-id))
   #     secret_access_key: ((aws-sandbox-secret-access-key))
   #     skip_download: true
   and
   # - put: ce-pdf-spike
   #   params:
   #     file: artifacts/*.pdf
   #     acl: public-read
   #     content_type: application/pdf
   #   on_success:
   #     put: output-producer-updater
   #     params:
   #       id: output-producer-queued/id
   #       status_id: "5" # Completed
   #       pdf_url: book/pdf_url
   #   on_failure:
   #     put: output-producer-updater
   #     params:
   #       id: output-producer-queued/id
   #       status_id: "4" # Failed

5. run:

.. code-block:: bash

   fly -t local-pipeline-stuff set-pipeline -p pdf-producer -c pipeline.yml

and if needed, run:

.. code-block:: bash

   fly -t local-pipeline-stuff unpause-pipeline -p pdf-producer

6. if pipeline does not work, run:

.. code-block:: bash

   fly -t local-pipeline-stuff destroy-pipeline -p pdf-producer

and then run:

.. code-block:: bash

   fly -t local-pipeline-stuff set-pipeline -p pdf-producer -c pipeline.yml
