Getting Started
===============

.. _manual_installation:

Manual Installation
-------------------
To test out the current code you will need the following installed:

* Python2.7 or Python3.1+
* virtualenv
* etcd2 (running)
* OpenShift or Kubernetes Cluster (running)
* (Optional) docker (running)

Set up virtualenv
~~~~~~~~~~~~~~~~~

.. include:: examples/setup_virtualenv.rst

(Optional): Run Unittests
~~~~~~~~~~~~~~~~~~~~~~~~~
If you are running from the matest master it's a good idea to verify that all
the unittests run. From the repo root...

.. include:: examples/run_unittest_example.rst


Setup Overlay Network Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Flannel requires a configuration inside of etcd.

.. include:: examples/flannel_overlay_network_example.rst


(Optional) Set The OpenShift or Kubernetes Access Method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are two methods for accessing the container manager: Client Side Certificate and Bearer Token. Only one is needed when working with a secured Kubernetes installation.

(Recommended) Client Certificate
````````````````````````````````

To configure a client certificate:

.. note:: There is no default for the client certificate!

.. include:: examples/config_kube_client_side_certificate.rst

Bearer Token
````````````

To configure a Bearer token:

.. note:: There is no default for the bearer token!

.. include:: examples/config_kube_bearer_token.rst


(Optional): Build Docker Container
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If you want to run from Docker and would like to build the image for yourself run...

.. code-block:: shell

    docker build --tag commissaire .
    ...

Running the service
~~~~~~~~~~~~~~~~~~~

Most of Commissaire's command-line options can be specified in a JSON
configuration file, by default ``/etc/commissaire/commissaire.conf`` or
as specified by the ``--config-file`` option.

.. note::

   Command-line options take precedence over the configuration file.

.. note::

   The URI you give for etcd and Kubernetes via the CLI will be fed into the
   configuration files on remote host nodes. Make sure to use the public IP of
   the etcd and Kubernetes hosts.

From Source
```````````
To launch the server from the repo root, with a configuration file such
as those given below:

.. include:: examples/run_from_source.rst

**Not So Secure Configuration**

.. include:: examples/insecure_config.rst

**More Secure Configuration**

.. note::

   Using client side certificates to access etcd/kubernetes will require proper configuration within etcd/kubernetes.

   Also, this example shows placing hashed user passwords in a separate `users.json` file, presumably with more restrictive access permissions.

.. include:: examples/secure_config.rst


Via Docker
``````````
To run the image, place a ``commissaire.conf`` file (see the examples above)
in an empty directory and then bind-mount the directory to ``/etc/commissaire``
in the container.

Similarly, if you are using client-side certificates, place the certificate
files in an empty directory and then bind-mount the directory inside the
container (shown below as ``/certs``), making sure all the certificate path
settings in ``commissaire.conf`` use the bind-mounted directory path.

.. include:: examples/run_via_docker.rst

.. note::

   Make sure that your firewall allows access to the etcd and kubernetes hosts and ports!


Adding a Cluster
~~~~~~~~~~~~~~~~
Verify that Commissaire is running as a container or in the virtual environment then execute...

.. include:: examples/create_cluster.rst

Adding a Host
~~~~~~~~~~~~~
Verify that Commissaire is running as a container or in the virtual environment then execute...

.. include:: examples/create_host.rst
