Overview
========

.. pull-quote::

   It actually configured Kubernetes when I could not remember how to.

   -- Ryan Cook

commissaire is a lightweight REST interface for upgrading, restarting, and bootstrapping new hosts into an existing Container Management cluster.

Feature Overview
----------------

- Restart hosts in a container cluster
- Upgrade hosts in a container cluster
- Bootstrap new hosts into an existing container cluster
- No agent required for hosts: All communication is done over SSH
- Simple REST interface for automation
- Service status for health checking
- Plug-in based authentication framework
- Command line interface for operators
- Built in support for Atomic, RHEL, Fedora, and CentOS


Flow
----

.. image:: commissaire-flow-diagram.png


What commissaire Is Not
-----------------------
There are a lot of overloaded words in technology. It's important to note what 
commissaire is not as much as what it is. commissaire is not:

- A Container Manager or scheduler (such as kubernetes)
- A configuration management system (such as ansible or puppet)
- A replacement for individual host management systems


Example Uses
------------

.. note::

   This is an early list. More use cases will be added in the future.

- An administrator needs to upgrade an entire group of hosts acting as kubernetes nodes
- An administrator needs to restart an entire group of hosts acting as kubernetes nodes
- An organization would like new hosts to register themselves into a kubernetes cluster upon first boot without administrator intervention
- An organization would like to keep groups of hosts used as kubernetes nodes out of direct control of anything but kubernetes and basic operations.
