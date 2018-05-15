FROM python:3.6.0-alpine

MAINTAINER Akiel <akiel@aleph.engineering>

LABEL version='1.0'
LABEL description='AnnoyingOrangeBot'

ADD libs /home/libs
COPY requirements.txt /home/
RUN pip3 install --no-index --find-links="/home/libs" -r /home/requirements.txt

ADD . /home/

WORKDIR /home/

ENTRYPOINT ["/usr/local/bin/python", "main.py"]