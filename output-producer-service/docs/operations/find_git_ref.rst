.. _operations-find-git-ref:

############
Find Git-Ref
############

When code is merged to a CORGI-related repository docker images are built and labeled with an auto-generated *tag*, 
by the `ce-image-autotag pipeline <https://concourse-v6.openstax.org/teams/CE/pipelines/ce-image-autotag>`_. 
During the build we add labels to images containing the git-refs.

**************
Git-Ref by Tag
**************

*Tags* can be discovered through Concourse (:ref:`operations-select-code-version-tag`) or DockerHub 
(i.e. `openstax/cops-bakery-scripts <https://hub.docker.com/repository/docker/openstax/cops-bakery-scripts/>`_).  

**Query a git-ref with given a** `tag` **,** ``20201020.175757`` **, with** ``docker inspect`` **:**

.. code-block:: bash

    docker inspect openstax/cops-bakery-scripts:20201020.175757

**The above** ``docker inspect`` **command should return git-refs for each CORGI-related repository:**

.. code-block:: bash

    "Labels": {
                "maintainer": "OpenStax Content Engineering",
                "version_cops": "f85f04e",
                "version_cops_resource": "f319db0",
                "version_easybake": "7341d52",
                "version_mathify": "1858333",
                "version_neb": "2f17ed0",
                "version_princexml": "222be11",
                "version_recipes": "v1.63.0",
                "version_xhtml_validator": "cb49119"
            }

.. note:: Another way to find a git-ref would be from the 
    `ce-image-autotag pipeline <https://concourse-v7.openstax.org/teams/CE/pipelines/ce-image-autotag>`_.
    However, this can be a bit of a pain if it’s not the most recent-ish build.
