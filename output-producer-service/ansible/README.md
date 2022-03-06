# cops-deployment

The set of ansible playbooks and roles used to configure and deploy the Content Output Producer Service (COPS)

This README is mostly for development purposes on the playbook itself. If you are looking to do a deployment please reference the `operations` section of the docs.

## Local development and testing

1. Download and install [Virtualbox](https://www.virtualbox.org/wiki/Downloads)
2. Download and install [Vagrant](https://www.vagrantup.com/downloads.html)
3. Install [Ansible](http://docs.ansible.com/ansible/latest/intro_installation.html)
4. Open a terminal window and run: `vagrant up`

When the `vagrant up` is executed it will create a new VM, install the base box, and provision it using the ansible playbook defined in `main.yml`.

Upon completion of the provisioning process (`vagrant up` is complete and you're back at the terminal prompt), you can log into the VM via SSH by running `vagrant ssh`.
