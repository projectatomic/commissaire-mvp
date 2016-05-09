
.. code-block:: shell

   (virtualenv)$ cat /etc/commissaire/commissaire.conf
   {
       "etcd-uri": "http://192.168.152.100:2379",
       "kube-uri": "http://192.168.152.101:8080",
       "authentication-plugin": {
           "name": "commissaire.authentication.httpbasicauth",
           "users": {
               "a": {
                   "hash": "$2a$12$GlBCEIwz85QZUCkWYj11he6HaRHufzIvwQjlKeu7Rwmqi/mWOpRXK"
               }
           }
       }
   }
