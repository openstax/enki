.. _operations-setting-up-the-swarm:

################
Set Up The Swarm
################

CORGI utilizes :term:`Container Orchestration` provided by `Docker Swarm <https://docs.docker.com/engine/swarm/>`_ to manage 
and deploy the various services that comprise the system. 

In order to deploy CORGI and to take advantage of everything container orchestration has to offer we must first:

1. Install Docker-CE on each host
2. Initialize Swarm Mode on each host
3. Setup Main Traefik Service

After set up of the servers with swarm we can then :ref:`operations-updating-the-stack` to the swarm servers.

This document will assume that the server operating system is `Ubuntu 18.04 (Bionic Beaver) <https://releases.ubuntu.com/18.04.4/>`_ and proper user permissions and SSH access has already been established.

.. note:: 

   This process is mostly done manual but we will be porting these steps over to 
   using :term:`Ansible`. Currently, the only step using Ansible is to
   :ref:`operations-cleaning-up-the-swarm`

----

*************
Prerequisites
*************

Install Docker
==============

Run the following commands to install Docker:

.. code-block:: bash

   # Update Local Database
   sudo apt-get update

.. code-block:: bash

   # Download Dependencies
   sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common

.. code-block:: bash

   # Add Docker's GPG Key
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add --

.. code-block:: bash

   # Install Docker Repository
   sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu  $(lsb_release -cs)  stable"

.. code-block:: bash
   
   # Update Repositories
   sudo apt-get update

----


*****************
Install Docker-CE
*****************

Run the following commands to install Docker-CE:

.. code-block:: bash

   # Install Docker-CE
   sudo apt-get install docker-ce

.. code-block:: bash

   # Add User to Docker Group
   sudo usermod -aG docker $USER

.. code-block:: bash

   # Test Docker
   docker run hello-world

.. warning:: If a permission error occurs the server may need to be restarted.

----


*******************
Create Docker Swarm
*******************

.. important:: The following ports need to be available on the master and worker nodes.

   | **TCP port 2376** 
   | For secure communication to Docker Client.
   | Required for Docker Machine work and orchestrate Docker hosts.
   |
   | **TCP port 2377** 
   | For communication between nodes of a Docker Swarm or cluster.
   | Only needs to be opened on manager nodes.
   |
   | **TCP and UDP port 7946** 
   | For communication among nodes (container network discovery).
   |
   | **UDP port 4789** 
   | For overlay network traffic (container ingress networking).

**STEP 1: SSH into the server you'd like to initialize as the swarm master.**

**STEP 2: Initialize Docker Swarm on Node**

Initialize master node on server:

.. code-block:: bash

   docker swarm init

Successful run will produce the following:

.. code-block:: shell-session

   Swarm initialized: current node (xxxxxxxxxxxxxxxxxx) is now a manager.

   To add a worker to this swarm, run the following command:

       docker swarm join --token SWMTKN-1-xxxxxxxxxxxxxxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxx xxx.xx.xxx.xxx:2377

   To add a manager to this swarm, run 'docker swarm join-token manager' and follow the instructions.

.. note:: ``docker swarm init`` initiates the server as the Master Node of the swarm and provides a ``docker swarm join ..`` command to join all other hosts intended to be part of the swarm as worker nodes.
   

**STEP 3: Join Worker Nodes to Swarm**

Copy ``docker swarm join`` command with token from ``docker swarm init`` output

.. code-block:: shell-session

   docker swarm join --token SWMTKN-1-xxxxxxxxxxxxxxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxx xxx.xx.xxx.xxx:2377

Paste ``docker swarm join..`` command into a terminal window of all other nodes in the swarm.

----

***************************
Create Main Traefik Service
***************************

.. important:: A `DevOps Request <https://github.com/openstax/cnx/wiki/Making-DevOps-Requests>`_ 
   needs to be made in order for devops to add the openstax.cert and openstax.pem 
   files to the server.

**STEP 1: Connect via SSH to a master node in swarm**

**STEP 2: Create node environment variable**

.. code-block:: bash

   export NODE_ID=$(docker info -f '{{.Swarm.NodeID}}')

**STEP 3: Add labels to the master node in the swarm**

.. code-block:: bash

   docker node update --label-add proxy=true $NODE_ID
   docker node update --label-add app-db-data=true $NODE_ID

.. note:: Traefik and database containers will always be started on this node.


**STEP 4: Create shared network for Traefik and containers deployed as part of stack**

.. code-block:: bash

  docker network create --driver=overlay traefik-public

**STEP 5: Create Traefik Service:**

.. code-block:: bash

   docker service create \
     --name traefik \
     --constraint=node.labels.proxy==true \
     --publish 80:80 \
     --publish 443:443 \
     --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
     --mount type=bind,source=/etc/ssl,target=/etc/ssl \
     --network traefik-public \
     --label "traefik.enable=true" \
     --label "traefik.tags=traefik-public" \
     --label "traefik.docker.network=traefik-public" \
     --label "traefik.redirectorservice.frontend.entryPoints=http" \
     --label "traefik.redirectorservice.frontend.redirect.entryPoint=https" \
     --label "traefik.webservice.frontend.entryPoints=https" \
     traefik:v1.7 \
     --docker \
     --docker.swarmmode \
     --docker.watch \
     --docker.exposedbydefault=false \
     --constraints=tag==traefik-public \
     --entrypoints='Name:http Address::80 Redirect.EntryPoint:https' \
     --entrypoints='Name:https Address::443 TLS:/etc/ssl/certs/openstax.crt,/etc/ssl/private/openstax.pem' \
     --logLevel=INFO \
     --accessLog

----

***********************
Set Up Required Secrets
***********************

The stack requires that the docker secret ``basic-auth-users`` is set in the swarm to work properly.
An example of creating basic auth credentials with a single user is the following, when ``DOCKER_HOST`` is properly pointing to the running swarm:

.. code-block:: bash

  htpasswd -nbB <username> <password> | docker secret create basic-auth-users -
