Docker Custodian
================

Keep docker hosts clean and tidy.


dcgc
----

Remove old docker containers and docker images.

``dcgc`` will remove stopped containers and unused images that are older than
"max age".  Running containers, and images which are used by a container are
never removed.

Maximum age can be specificied with any format supported by
`pytimeparse <https://github.com/wroberts/pytimeparse>`_.

Example:

    dcgc --max-container-age 3days --max-image-age 30days


dcstop
------

Stop containers that have been running for too long.

``dcstop`` will ``docker stop`` containers where the container name starts
with `--prefix` and it has been running for longer than `--max-run-time`.


Example:

    dcstop --max-run-time 2days --prefix "projectprefix_"
