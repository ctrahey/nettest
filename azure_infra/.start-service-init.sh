#! /usr/bin/env bash
apt-get update
apt install -y docker.io
docker run --restart always -p 80:80 ctrahey/nettest:www-python-fastapi
