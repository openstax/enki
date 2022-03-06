.. _operations-overview:

##############
Overview (WIP)
##############

The CORGI Swarm lives on Openstax's Production AWS EC2 server.

A developer will :ref:`operations-updating-the-stack` to production (AWS EC2) where 
the docker swarm lives. 

To do this the developer will set up their local machine and use Bastion2 (Prod Server)
as a jump host to bypass the AWS server firewall to deploy, with permissions (IdentityFile) that live on 
their local machine.

.. note:: 
    The only pipeline deployed on the AWS EC2 server is the PDF pipeline, 
    the distribution pipeline is still in development.

(WIP) Add nice diagram created by JP here.




