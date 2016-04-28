.. code-block:: shell

    $ cat /path/to/config/commissaire.conf
    {
        "etcd-uri": "https://192.168.152.100:2379",
        "kube-uri": "https://192.168.152.101:8080",
        "tls-certfile": "/certs/server.crt",
        "tls-keyfile": "/certs/server.key",
        "etcd-cert-path": "/certs/etcd.crt",
        "etcd-cert-key-path": "/certs/etcd.key"
    }

    $ sudo docker run -d \
        -p 8000:8000
        -v /path/to/config:/etc/commissaire \
        -v /path/to/etcd/certificates:/certs \
        commissaire
    ...
