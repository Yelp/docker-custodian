.PHONY: all clean tag test

PACKAGE_VERSION=$(shell python setup.py --version)

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
