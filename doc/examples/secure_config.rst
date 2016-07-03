.. note::

   Using client side certificates to access etcd/kubernetes will require proper configuration within etcd/kubernetes.

   Also, this example shows placing hashed user passwords in a separate `users.json` file, presumably with more restrictive access permissions.

.. code-block:: javascript

   {
       "tls-keyfile": "/path/to/server.key",
       "tls-certificate": "/path/to/server.crt",
       "etcd-uri": "https://192.168.152.100:2379",
       "etcd-cert-path": "/path/to/etcd_clientside.crt",
       "etcd-cert-key-path": "/path/to/etcd_clientside.key",
       "kube-uri": "https://192.168.152.101:8080",
       "authentication-plugin": {
           "name": "commissaire.authentication.httpbasicauth",
           "filepath": "conf/users.json"
       }
   }

