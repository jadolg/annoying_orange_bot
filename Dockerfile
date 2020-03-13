FROM python:3.7.0-alpine

MAINTAINER Akiel <akiel@aleph.engineering>

LABEL version='1.0'
LABEL description='AnnoyingOrangeBot'
RUN apk update && apk add tzdata gcc musl-dev \
     && cp -r -f /usr/share/zoneinfo/Cuba /etc/localtime
ADD requirements.txt /home/
WORKDIR /home/
RUN pip3 install -r requirements.txt

ADD . /home/


ENTRYPOINT ["/usr/local/bin/python", "main.py"]
