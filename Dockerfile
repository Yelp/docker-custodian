FROM    alpine:3.2
MAINTAINER Kyle Anderson <kwa@yelp.com>

RUN     apk add -U python py-pip
ADD     requirements.txt /code/requirements.txt
RUN     pip install -r /code/requirements.txt
ADD     docker_custodian/ /code/docker_custodian/
ADD     setup.py /code/
RUN     pip install --no-deps -e /code
