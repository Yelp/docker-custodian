Docker Custodian
================

.. |tests badge| image:: https://github.com/yelp/docker-custodian/actions/workflows/tests.yml/badge.svg
.. |docker badge| image:: https://github.com/yelp/docker-custodian/actions/workflows/docker.yml/badge.svg
.. |pypi badge| image:: https://github.com/yelp/docker-custodian/actions/workflows/publish.yml/badge.svg

|tests badge| |docker badge| |pypi badge|

Keep docker hosts tidy.


.. contents::
    :backlinks: none

Install
-------

There are three installation options

Container
~~~~~~~~~

.. code::

    docker pull yelp/docker-custodian
    docker run -ti \
        -v /var/run/docker.sock:/var/run/docker.sock \
        yelp/docker-custodian --help

Debian/Ubuntu package
~~~~~~~~~~~~~~~~~~~~~

First build the package (requires `dh-virtualenv`)

.. code:: sh

    dpkg-buildpackage -us -uc

Then install it

.. code:: sh

    dpkg -i ../docker-custodian_*.deb


pypi.org
~~~~~~~~

.. code:: sh

    pip install docker-custodian


dcgc
----

Remove old docker containers and docker images.

``dcgc`` will remove stopped containers and unused images that are older than
"max age".  Running containers, and images which are used by a container are
never removed.

Maximum age can be specificied with any format supported by
`pytimeparse <https://github.com/wroberts/pytimeparse>`_.

Example:

.. code:: sh

    dcgc --max-container-age 3days --max-image-age 30days


Prevent images from being removed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``dcgc`` supports an image exclude list. If you have images that you'd like
to keep around forever you can use the exclude list to prevent them from
being removed.

::

    --exclude-image
        Never remove images with this tag. May be specified more than once.

    --exclude-image-file
        Path to a file which contains a list of images to exclude, one
        image tag per line.

You also can use basic pattern matching to exclude images with generic tags.

.. code::

    user/repositoryA:*
    user/repositoryB:?.?
    user/repositoryC-*:tag


Prevent containers and associated images from being removed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``dcgc`` also supports a container exclude list based on labels.  If there are
stopped containers that you'd like to keep, then you can check the labels to
prevent them from being removed.

::

    --exclude-container-label
        Never remove containers that have the label key=value. =value can be
        omitted and in that case only the key is checked. May be specified
        more than once.

You also can use basic pattern matching to exclude generic labels.

.. code::

    foo*
    com.docker.compose.project=test*
    com.docker*=*bar*


dcstop
------

Stop containers that have been running for too long.

``dcstop`` will ``docker stop`` containers where the container name starts
with `--prefix` and it has been running for longer than `--max-run-time`.


Example:

.. code:: sh

    dcstop --max-run-time 2days --prefix "projectprefix_"
