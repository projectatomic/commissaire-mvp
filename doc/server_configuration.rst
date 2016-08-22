Server Configuration
====================

Commissaire uses a JSON-formatted configuration file typically named
``/etc/commissaire/commissaire.conf``, the content of which is a JSON
object.

This section explains all recognized JSON object members and nested objects.

An example configuration file:

.. include:: examples/secure_config.rst

Socket Options
--------------

``listen-interface`` / ``listen-port``

  Specifies the IP address and port number on which the Commissaire
  server should listen for incoming connections.  These default to
  address ``0.0.0.0`` (all interfaces) on port ``8000``.

``tls-certfile`` / ``tls-keyfile``

  Specifies an absolute path to the Transport Layer Security (TLS)
  certificate and key file, respectively.  These have no defaults.

``tls-clientverifyfile``

  Specifies an absolute path to a file containing the Transport Layer
  Security (TLS) Certificate Authorities that client certificates should
  be verified against.  This has no default.

.. _authplugin:

authentication-plugin
---------------------

The ``authentication-plugin`` member is a nested object specifying how
clients must authenticate themselves to the Commissaire server.

The nested object requires at least a ``name`` member.  Other members
are specific to the authentication plugin.

``name``

  Specifies the Python module to serve as an authentication plugin.

  Commissaire provides several built-in choices, but also allows for 3rd
  party plugins.  The :ref:`Authentication Plugins <authdevel>` section
  explains how to write a new authentication plugin.

  The built-in plugin names are:

    * ``commissaire.authentication.httpbasicauth``
    * ``commissaire.authentication.httpauthclientcert``
    * ``commissaire.authentication.kubeauth``

commissaire.authentication.httpbasicauth
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enables `Basic Authentication <https://en.wikipedia.org/wiki/Basic_access_authentication>`_
using a specific configuration structure:

.. code-block:: javascript

   {
       "username(string)": {
           "hash": "bcrypthash(string)"
       }...
   }

The ``commctl`` program has a :ref:`built-in command for creating bcrypt
hashes <commctl_passhash>`.

``filepath``

  Specifies an absolute path to another JSON file (presumably with more
  restrictive access permissions) containing user names and hashed passwords
  in the format shown above.

  The ``filepath`` and ``users`` members are mutually exclusive.

``users``

  Directly embeds user names and hashed passwords as a nested JSON object
  in the format shown above.

  The ``filepath`` and ``users`` members are mutually exclusive.

commissaire.authentication.httpauthclientcert
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Accepts a certificate from the authenticating client.

``cn``

  Specifies the Common Name to match on the client certificate.  This has
  no default and is optional.  If omitted, the client certificate's Common
  Name is not examined.

.. _kubeauth:

commissaire.authentication.kubeauth
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Enables `Bearer Token Authentication <https://tools.ietf.org/html/rfc6750#section-2.1>`_
which comes from Kubernetes.

``resource``

  Specifies the Kubernetes resource used to check authentication against.
  This defaults to ``/serviceaccounts``.

register-store-handler
-----------------------

The ``register-store-handler`` member is a nested object or a *list* of nested
objects specifying where Commissaire data is to be stored.

Most common configurations will only need one storage handler.  But different
types of data *can be* partitioned across different types of storage handlers,
as defined by each handler's ``models`` list.

If the ``register-store-handler`` member is omitted, Commissaire uses a
default configuration equivalent to:

.. code-block:: javascript

   "register-store-handler": [
       {
           "name": "commissaire.store.kubestorehandler",
           "server_url": "http://127.0.0.1:8080",
           "models": ["*"],
       },
       {
           "name": "commissaire.store.etcdstorehandler",
           "server_url": "http://127.0.0.1:2379",
           "models": [],
       }
   ]

As with the :ref:`authentication-plugin <authplugin>` member above, each
nested object requires at least a ``name`` member and optionally a ``models``
member.  Other members are specific to the storage handler.

``name``

  Specifies the Python module to serve as a storage handler.

  Commissaire provides a couple built-in choices:

    * ``commissaire.store.etcdstorehandler``
    * ``commissaire.store.kubestorehandler``

``models``

  Specifies the data models assigned to the storage handler, expressed
  as a list of model names.  For convenience the model names can use
  glob-style wildcards "*" and "?".  This defaults to ``['*']``, which
  assigns all available data models to a single storage handler.

  See the :ref:`REST endpoints <rest_endpoints>` section for a complete
  list of model names.  Typical wildcard patterns for models include
  ``"Host*"`` and ``"Cluster*"``.

.. note::

  A data model may only be assigned to one storage handler.  Keep this
  in mind when using wildcards.

commissaire.store.etcdstorehandler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This handler stores data in etcd under the top-level key ``/commissaire``.

``server_url``

  Specifies the URL (``scheme://host:port``) of the etcd server.  This
  defaults to ``http://127.0.0.1:2379``.

``certificate-path`` / ``certificate-key-path``

  Specifies an absolute path to the client-side certificate and key file
  (respectively) for authenticating to the etcd server.  These have no
  defaults.  If used, the URL scheme in ``server_url`` must be ``https``.

commissaire.store.kubestorehandler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This handler stores data as metadata annotations on Kubernetes nodes.

``server_url``

  Specifies the URL (``scheme://host:port``) of the Kubernetes server.
  This defaults to ``http://127.0.0.1:8080``.

``certificate-path`` / ``certificate-key-path``

  Specifies an absolute path to the client-side certificate and key file
  (respectively) for authenticating to the Kubernetes server.  These have
  no defaults.  If used, the URL scheme in ``server_url`` must be ``https``.

``token``

  Specifies a bearer token for authenticating to the Kubernetes server.
  This has no default.
