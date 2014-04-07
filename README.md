Socket-activate Proxy
=====================

`sdproxy` is a [gevent][]-based proxy that cooperates with
[systemd][]'s socket activation feature.  It is functionally
similar to [systemd-socket-proxy][], except:

- It is less featureful
- It is less robust

Also, it is written in Python, so it may even be less performant.  I
wrote it mostly as an example, and also because
[systemd-socket-proxy][] isn't currently packaged for Fedora 19..

[systemd-socket-proxy]: [http://www.freedesktop.org/software/systemd/man/systemd-socket-proxyd.html
[gevent]: http://gevent.org/
[systemd]: http://www.freedesktop.org/wiki/Software/systemd/

Example
=======

Given a socket file like this in `webproxy.socket`:

    [Socket]
    ListenStream=80

    [Install]
    WantedBy=sockets.target

And the following service in `webproxy.service`:

    [Unit]
    Description=Web server proxy
    After=network.target

    [Service]
    ExecStart=/bin/sdproxy --idle-timeout 60 www.example.com 8080
    Type=simple
    Restart=on-failure

    [Install]
    WantedBy=multi-user.target

The a connection on port 80 will cause the proxy to run and start
accepting and handling connections.  If there is no traffic for more
than a minute, the proxy will exit and will be re-launched by
`systemd` when necessary.

