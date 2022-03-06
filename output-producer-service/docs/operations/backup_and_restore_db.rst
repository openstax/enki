.. _operations-backup-up-and-restore-db:

###############################
Backup and Restore the Database
###############################

.. note::
     These instructions will assume the commands will be executed on a staging
     environment. Replace all references to ``staging`` with ``prod`` to indicate
     the production environment.

.. warning::
     We are currently working towards using AWS RDS to replace the way we are using
     a postgres container. These instructions may become out of date so ensure before
     you start that these are accurate.

*************
Prerequisites
*************

- Ensure you have followed the instructions in the first section of this page:
  :ref:`Prerequisite Updating the Stack<Prereq Update the Stack>`. You should be
  able to run the docker commands used in the rest of the article.
- Install `jq <https://stedolan.github.io/jq/>`_.

*******************
Backup the Database
*******************

Check Connection to Swarm
=========================

Ensure we can connect to the CORGI manager instance.

.. code-block:: bash

   docker -H ssh://corgi info -f '{{.Swarm.NodeID}}'

You should see output the resembles the following:

.. code-block:: bash

   cupwsrlecgdz3rptrqypc8x1v

Now that we can get the ``NodeID`` we can continue to find the database container that is running
our database.

Find the database container
===========================

We'll execute the following command:

.. code-block:: bash

   docker -H ssh://corgi stack services corgi_stag

You should see the following result:

.. code-block:: bash

    ID             NAME                  MODE         REPLICAS   IMAGE                                               PORTS
    cldj5exbaw01   corgi_stag_backend    replicated   2/2        openstax/output-producer-backend:20210913.154927
    cqqt3wb35mqv   corgi_stag_db         replicated   1/1        postgres:12
    wlhqpf656ykh   corgi_stag_frontend   replicated   2/2        openstax/output-producer-frontend:20210913.154927
    a0k806brkral   corgi_stag_proxy      replicated   1/1        traefik:v1.7

We have all the services running. The one that we are primarily interested in is the one labeled
``corgi_stag_db``. However, this information is not enough to run the commands that we need to do the database backup.


Set the $DB_CONTAINER
=====================

A way to get the correct container is to grep based on all the containers that are running on the node and awk the
output in order to find the name:

.. code-block:: bash

    # Print the name of the container
    docker -H ssh://corgi ps | grep corgi_stag_db | awk '{ print $11 }'

    # Export the $DB_CONTAINER to an environment variable for future use
    export DB_CONTAINER=$(docker -H ssh://corgi ps | grep corgi_stag_db | awk '{ print $11 }')
    echo "$DB_CONTAINER"
    corgi_stag_db.1.yssodl9rgl5tg54zxa2id549c

Create the backup
=================

Create the backup using the following command utilizing ``pg_dump``:

.. code-block:: bash

    docker -H ssh://corgi exec -it $DB_CONTAINER pg_dump -h db -U postgres -h db --no-owner cops > corgi-stag-db.backup.sql

********************
Restore the Database
********************

.. warning::
    Ensure you've created a database dump file as described in :ref:`Backup the Database`.

Prepare the environment
=======================

Refer to the sections in :ref:`Set the $NODE_ID` and :ref:`Set the $DB_CONTAINER` to set both these
environment variables before you start if you haven't already.

- ``NODE_ID``
- ``DB_CONTAINER``

Copy the backup file onto the container volume
==============================================

We need to copy the backup file we have located on our host machine to the volume that is mounted to the docker
container. We can do that using the ``docker copy`` command:

.. code-block:: bash

    docker -H ssh://corgi cp corgi-stag-db.backup.sql $DB_CONTAINER:/var/lib/postgresql/data

Restore the backup
==================

Restore the database backup by piping the database backup file to the psql command:

.. code-block:: bash

    docker -H ssh://corgi exec -it $DB_CONTAINER psql -U postgres -h db -d cops -f /var/lib/postgresql/data/corgi-stag-db.backup.sql
