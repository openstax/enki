.. image:: ./_static/images/corgi.jpg
   :scale: 50%
   :alt: CORGI
   :align: center

----

######################################################
Content Output Review and Generation Interface (CORGI)
######################################################

CORGI an overarching system that contain different ways to 
produce Openstax book content for various users (Content Manangers (CMs), 
QA, and developers) to consume. A book is typically called a collection by Content
Managers and others that work directly with content.

****************
CORGI at a Glance
****************
+----------------+-----------------+-----------+-----------+-----------+
| Output         | Users           | More Info | More Info | More Info |
+================+=================+===========+===========+===========+
| PDF            | CMs, CE Styles  | blah blah | blah blah | blah blah |
+----------------+-----------------+-----------+-----------+-----------+
| Distribution   | Rex, Tutor      | etc etc e | etc etc e | etc etc e |
+----------------+-----------------+-----------+-----------+-----------+

.. note::
   | **June 3rd, 2020**  
   | The PDF Pipeline is in production. The Distribution Pipeline is still being developed. 

.. toctree::
   :maxdepth: 2
   :caption: CORGI Operations
   :hidden:

   operations/overview
   operations/setting_up_the_swarm
   operations/updating_the_stack
   operations/cleaning_up_the_swarm
   operations/updating_bakery_scripts
   operations/generate_pipeline_config
   operations/cli
   operations/find_git_ref
   operations/select_code_version_tag
   operations/backup_and_restore_db

.. toctree::
   :maxdepth: 2
   :caption: PDF System
   :hidden:

   pdf/overview
   pdf/steps
   pdf/backend_architecture
   pdf/frontend_ui

.. toctree::
   :maxdepth: 2
   :caption: Distribution System
   :hidden:

   distribution/overview
   distribution/dev-steps
   distribution/prod-steps

.. toctree::
   :maxdepth: 2
   :caption: Quality Assurance
   :hidden:

   qa/setup

.. toctree::
   :maxdepth: 2
   :caption: Extras
   :hidden:

   glossary

Tech Resources
==============
* `AWS S3 <https://aws.amazon.com/s3/>`_
* `AWS EC2 <https://aws.amazon.com/ec2/>`_
* `AWS Cloudfront <https://aws.amazon.com/cloudfront/>`_
* `Traefik <https://containo.us/traefik/>`_
* `Docker <https://www.docker.com/>`_
* `Docker Swarm <https://docs.docker.com/engine/swarm/>`_
* `Docker Hub <https://hub.docker.com/>`_
* `FAST API <https://fastapi.tiangolo.com/>`_
* `VUE.js <https://vuejs.org/>`_
* `Concourse <https://concourse-ci.org/>`_
* `Sphinx Docs <https://www.sphinx-doc.org/en/master/>`_
* `ConEng wiki <https://github.com/openstax/cnx/wiki>`_ 


Indices and Tables
==================

* :ref:`modindex`
* :ref:`genindex`
