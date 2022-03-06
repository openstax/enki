.. _operations-updating-bakery-scripts:

#######################
Update Pipeline Scripts 
#######################

All scripts that CORGI Concourse pipeline tasks may use to complete jobs live in Docker Image `openstax/cops-bakery-scripts <https://hub.docker.com/repository/docker/openstax/cops-bakery-scripts>`_. 
built from `bakery/src/scripts/ <https://github.com/openstax/output-producer-service/tree/master/bakery/src/scripts>`_ 
directory in the `openstax/output-producer-service <https://github.com/openstax/output-producer-service/>`_ repository/ project.

All output pipelines (pdf, distribution, etc) use the same Docker Image. 
The scripts are not limited to baking tasks as the name would suggest.

----

Development
===========

Build Image with Changes
------------------------

1. Have ``bakery/src/scripts`` as your working directory
2. Make the desired change in the ``bakery/src/scripts/*.py`` file
3. Build the image with ``docker build .``

The Hard Way
-------------
4. Push up to docker hub
5. :ref:`operations-generate-pipeline-config`
6. Find and replace ``openstax/cops-bakery-scripts`` in config file to your image
7. Set desired pipeline:
   
   - :ref:`pdf-pipeline-steps`
   - :ref:`distribution-pipeline-steps`

The Alternate Way
-----------------

4. Alternatively the better way (recently implemented) - 
https://github.com/openstax/output-producer-service/tree/master/bakery#development-and-qa

----

Production
==========
When your code is reviewed and merged it will trigger our 
`ce-image-autotag pipeline <https://concourse-dev0.openstax.org/teams/Dev/pipelines/ce-image-autotag>`_
to build and tag a new docker image for `openstax/cops-bakery-scripts <https://hub.docker.com/repository/docker/openstax/cops-bakery-scripts>`_. 

After the image is built and tagged, a tag is returned and that is what is used to :ref:`operations-updating-the-stack`
