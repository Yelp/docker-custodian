#!/usr/bin/env python
"""
Stop docker container that have been running longer than the max_run_time and
match some prefix.
"""
import argparse
import logging
import sys

import dateutil.parser
import docker
import docker.errors
import requests.exceptions

from docker_custodian.args import timedelta_type
from docker.utils import kwargs_from_env


log = logging.getLogger(__name__)


def stop_containers(client, max_run_time, matcher, dry_run):
    for container_summary in client.containers():
        container = client.inspect_container(container_summary['Id'])
        name = container['Name'].lstrip('/')
        if (
            matcher(name) and
            has_been_running_since(container, max_run_time)
        ):

            log.info("Stopping container %s %s: running since %s" % (
                container['Id'][:16],
                name,
                container['State']['StartedAt']))

            if not dry_run:
                stop_container(client, container['Id'])


def stop_container(client, id):
    try:
        client.stop(id)
    except requests.exceptions.Timeout as e:
        log.warn("Failed to stop container %s: %s" % (id, e))
    except docker.errors.APIError as ae:
        log.warn("Error stopping %s: %s" % (id, ae))


def build_container_matcher(prefixes):
    def matcher(name):
        return any(name.startswith(prefix) for prefix in prefixes)
    return matcher


def has_been_running_since(container, min_time):
    started_at = container.get('State', {}).get('StartedAt')
    if not started_at:
        return False

    return dateutil.parser.parse(started_at) <= min_time


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout)

    opts = get_opts()
    client = docker.APIClient(version='auto',
                              timeout=opts.timeout,
                              **kwargs_from_env())

    matcher = build_container_matcher(opts.prefix)
    stop_containers(client, opts.max_run_time, matcher, opts.dry_run)


def get_opts(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--max-run-time',
        type=timedelta_type,
        help="Maximum time a container is allows to run. Time may "
        "be specified in any pytimeparse supported format."
    )
    parser.add_argument(
        '--prefix', action="append", default=[],
        help="Only stop containers which match one of the "
             "prefix."
    )
    parser.add_argument(
        '--dry-run', action="store_true",
        help="Only log actions, don't stop anything."
    )
    parser.add_argument(
        '-t', '--timeout', type=int, default=60,
        help="HTTP timeout in seconds for making docker API calls."
    )
    opts = parser.parse_args(args=args)

    if not opts.prefix:
        parser.error("Running with no --prefix will match nothing.")

    return opts


if __name__ == "__main__":
    main()
