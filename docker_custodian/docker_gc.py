#!/usr/bin/env python
"""
Remove old docker containers and images that are no longer in use.

"""
import argparse
import logging
import sys

import dateutil.parser
import docker
import docker.errors
import requests.exceptions

from docker_custodian.args import timedelta_type

log = logging.getLogger(__name__)


# This seems to be something docker uses for a null/zero date
YEAR_ZERO = "0001-01-01T00:00:00Z"


def cleanup_containers(client, max_container_age, dry_run):
    all_containers = get_all_containers(client)

    for container_summary in reversed(all_containers):
        container = api_call(client.inspect_container, container_summary['Id'])
        if not container or not is_container_old(container, max_container_age):
            continue

        log.info("Removing container %s %s %s" % (
            container['Id'][:16],
            container.get('Name', '').lstrip('/'),
            container['State']['FinishedAt']))

        if not dry_run:
            api_call(client.remove_container, container['Id'])


def is_container_old(container, min_date):
    state = container.get('State', {})
    if state.get('Running'):
        return False

    if state.get('Ghost'):
        return True

    # Container was created, but never used
    if (state.get('FinishedAt') == YEAR_ZERO and
            dateutil.parser.parse(container['Created']) < min_date):
        return True

    return dateutil.parser.parse(state['FinishedAt']) < min_date


def get_all_containers(client):
    log.info("Getting all continers")
    containers = client.containers(all=True)
    log.info("Found %s containers", len(containers))
    return containers


def get_all_images(client):
    log.info("Getting all images")
    images = client.images()
    log.info("Found %s images", len(images))
    return images


def cleanup_images(client, max_image_age, dry_run):
    # re-fetch container list so that we don't include removed containers
    image_tags_in_use = set(
        container['Image'] for container in get_all_containers(client))

    images = filter_images_in_use(get_all_images(client), image_tags_in_use)

    for image_summary in reversed(images):
        remove_image(client, image_summary, max_image_age, dry_run)


def filter_images_in_use(images, image_tags_in_use):
    def get_tag_set(image_summary):
        image_tags = image_summary.get('RepoTags')
        if no_image_tags(image_tags):
            # The repr of the image Id used by client.containers()
            return set(['%s:latest' % image_summary['Id'][:12]])
        return set(image_tags)

    def image_is_in_use(image_summary):
        return not get_tag_set(image_summary) & image_tags_in_use

    return list(filter(image_is_in_use, images))


def is_image_old(image, min_date):
    return dateutil.parser.parse(image['Created']) < min_date


def no_image_tags(image_tags):
    return not image_tags or image_tags == ['<none>:<none>']


def remove_image(client, image_summary, min_date, dry_run):
    image = api_call(client.inspect_image, image_summary['Id'])
    if not image or not is_image_old(image, min_date):
        return

    log.info("Removing image %s" % format_image(image, image_summary))
    if dry_run:
        return

    image_tags = image_summary.get('RepoTags')
    # If there are no tags, remove the id
    if no_image_tags(image_tags):
        api_call(client.remove_image, image_summary['Id'])
        return

    # Remove any repository tags so we don't hit 409 Conflict
    for image_tag in image_tags:
        api_call(client.remove_image, image_tag)


def api_call(func, id):
    try:
        return func(id)
    except requests.exceptions.Timeout as e:
        log.warn("Failed to call %s %s %s" % (func.__name__, id, e))
    except docker.errors.APIError as ae:
        log.warn("Error calling %s %s %s" % (func.__name__, id, ae))


def format_image(image, image_summary):
    def get_tags():
        tags = image_summary.get('RepoTags')
        if not tags or tags == ['<none>:<none>']:
            return ''
        return ', '.join(tags)

    return "%s %s" % (image['Id'][:16], get_tags())


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout)

    opts = get_opts()
    client = docker.Client(timeout=opts.timeout)

    if opts.max_container_age:
        cleanup_containers(client, opts.max_container_age, opts.dry_run)
    if opts.max_image_age:
        cleanup_images(client, opts.max_image_age, opts.dry_run)


def get_opts(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--max-container-age',
        type=timedelta_type,
        help="Maximum age for a container. Containers older than this age "
             "will be removed. Age can be specified in any pytimeparse "
             "supported format.")
    parser.add_argument(
        '--max-image-age',
        type=timedelta_type,
        help="Maxium age for an image. Images older than this age will be "
             "removed. Age can be specified in any pytimeparse supported "
             "format.")
    parser.add_argument(
        '--dry-run', action="store_true",
        help="Only log actions, don't remove anything.")
    parser.add_argument(
        '-t', '--timeout', type=int, default=60,
        help="HTTP timeout in seconds for making docker API calls.")
    return parser.parse_args(args=args)


if __name__ == "__main__":
    main()
