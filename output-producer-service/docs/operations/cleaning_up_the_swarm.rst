.. _operations-cleaning-up-the-swarm:

##################
Clean Up The Swarm
##################

Docker swarm does not come with any "garbage collection" for dangling 
volumes or unused containers that have been created during updates or after 
restarts.

.. warning:: **This has caused issues where the host nodes run out of hard drive storage. To 
   prevent this we have created an** :term:`Ansible` **playbook to configure a cronjob on the server.**

----

*************************
Clean Up Execute Location
*************************

There are two places you can run this 'Clean Up' Ansible playbook:

1. Localhost with Bastion2 as a Jumphost
2. Directly from Bastion2.cnx.org

----

Execute from LocalHost
======================
From **localhost**, using **bastion2** as a jumphost, you need: 

   1. **bastion2** set up as a :term:`JumpHost` (`Configure Jumphost Guide <https://github.com/openstax/cnx/wiki/Configure-bastion2.cnx.org-as-a-JumpHost>`_)
   2. Proper key to corgi servers in the correct directory
   3. Run following commands

      .. code-block:: bash

         $ cd ./ansible

         # Changes directory from project root to Ansible directory
         
      .. code-block:: bash
         
         $ python -m .venv venv

         # Creates virtual environment to install Ansible and dependencies

      .. code-block:: bash
                           
         $ source ./.venv/bin/activate

         # Activates the virtual environment

      .. code-block:: bash
                          
         (venv) $ pip install -r requirements.txt

         # Installs Dependencies

      .. code-block:: bash

         (venv) $ ansible-playbook -i inventory.jumphost.yml main.yml

         # Runs the Ansible playbook using bastion2 as jumphost
   
   3. Ensure good run with similar output:

      .. code-block:: bash

         PLAY [OpenStax CORGI deployment] ************************************************

         TASK [Gathering Facts] *********************************************************
         ok: [default]

         TASK [Create cronjob to do docker cleanup] *************************************
         changed: [default]

         PLAY RECAP *********************************************************************
         default  : ok=2    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0

----

Execute from bastion2.cnx.org
=============================
   
   1. Clone down copy of `output-producer-service repository <https://github.com/openstax/output-producer-service>`_ into your home directory
   2. Run following commands

      .. code-block:: bash

         $ cd ./ansible

         # Changes directory from project root to Ansible directory
         
      .. code-block:: bash
         
         $ python -m .venv venv

         # Creates virtual environment to install Ansible and dependencies

      .. code-block:: bash
                           
         $ source ./.venv/bin/activate

         # Activates the virtual environment

      .. code-block:: bash
                          
         (venv) $ pip install -r requirements.txt

         # Installs Dependencies

      .. code-block:: bash

         (venv) $ ansible-playbook -i inventory.yml main.yml

         # Runs the Ansible playbook directly from bastion2

   3. Ensure good run with similar output:

      .. code-block:: bash

         PLAY [OpenStax CORGI deployment] ************************************************

         TASK [Gathering Facts] *********************************************************
         ok: [default]

         TASK [Create cronjob to do docker cleanup] *************************************
         changed: [default]

         PLAY RECAP *********************************************************************
         default  : ok=2    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
