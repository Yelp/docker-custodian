.PHONY: all clean tag test

PACKAGE_VERSION = $(shell python setup.py --version)

DOCKER_REPO ?= ${USER}
BUILD_TAG ?= ${PACKAGE_VERSION}

all: test

clean:
	git clean -fdx -- debian
	rm -f ./dist
	find . -iname '*.pyc' -delete

tag:
	git tag v${PACKAGE_VERSION}

test:
	tox

tests: test


.PHONY: build
build:
	docker build -t ${DOCKER_REPO}/docker-custodian:${BUILD_TAG} .
