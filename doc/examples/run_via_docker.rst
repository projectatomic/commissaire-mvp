.. code-block:: shell

    $ cat /path/to/config/commissaire.conf
    {
        "etcd-uri": "http://192.168.152.100:2379",
        "kube-uri": "http://192.168.152.101:8080"
    }

    $ sudo docker run -d \
        -p 8000:8000 \
        -v /path/to/config:/etc/commissaire \
        commissaire
    ...
