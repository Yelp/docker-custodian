.PHONY: all changelog clean package tag test

PACKAGE_VERSION=$(shell python setup.py --version)

all: test

changelog:
	dch -v ${PACKAGE_VERSION} -D lucid -u low

clean:
	git clean -fdx -- debian
	rm -f ./dist
	make -C yelp_package clean
	find . -iname '*.pyc' -delete

dist:
	ln -sf yelp_package/dist ./dist

itest_%: dist
	make -C yelp_package $@

package: itest_lucid itest_precise itest_trusty

tag:
	git tag v${PACKAGE_VERSION}

test:
	tox
