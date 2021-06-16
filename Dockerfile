FROM python:3.9-alpine3.12

COPY requirements.txt /code/requirements.txt
RUN pip install -r /code/requirements.txt
COPY docker_custodian/ /code/docker_custodian/
COPY setup.py /code/
RUN pip install --no-deps -e /code

ENTRYPOINT ["dcgc"]
