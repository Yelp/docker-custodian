#!/usr/bin/env python
"""
Remove old docker containers and images that are no longer in use.

"""
import argparse
import collections
import fnmatch
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
        container = api_call(client.inspect_container,
                             container=container_summary['Id'])
        if not container or not should_remove_container(container,
                                                        max_container_age):
            continue

        log.info("Removing container %s %s %s" % (
            container['Id'][:16],
            container.get('Name', '').lstrip('/'),
            container['State']['FinishedAt']))

        if not dry_run:
            api_call(client.remove_container, container=container['Id'],
                     v=True)


def should_remove_container(container, min_date):
    state = container.get('State', {})

    if state.get('Running'):
        return False

    if state.get('Ghost'):
        return True

    # Container was created, but never started
    if state.get('FinishedAt') == YEAR_ZERO:
        created_date = dateutil.parser.parse(container['Created'])
        return created_date < min_date

    finished_date = dateutil.parser.parse(state['FinishedAt'])
    return finished_date < min_date


def get_all_containers(client):
    log.info("Getting all containers")
    containers = client.containers(all=True)
    log.info("Found %s containers", len(containers))
    return containers


def get_all_images(client):
    log.info("Getting all images")
    images = client.images()
    log.info("Found %s images", len(images))
    return images


def get_dangling_volumes(client):
    log.info("Getting dangling volumes")
    volumes = client.volumes({'dangling': True})['Volumes']
    log.info("Found %s dangling volumes", len(volumes))
    return volumes


def cleanup_images(client, max_image_age, max_tags_count,
                   dry_run, exclude_set):
    # re-fetch container list so that we don't include removed containers
    image_tags_in_use = set(
        container['Image'] for container in get_all_containers(client))

    images = filter_images_in_use(get_all_images(client), image_tags_in_use)
    images = filter_excluded_images(images, exclude_set)

    tags_counter = collections.Counter()
    for image_summary in images:
        exceeds_max_tags_count = check_exceeds_max_tags_count(
            image_summary,
            tags_counter,
            max_tags_count)
        remove_image(
            client,
            image_summary,
            max_image_age,
            exceeds_max_tags_count,
            dry_run)


def check_exceeds_max_tags_count(image_summary, tags_counter, max_tags_count):
    """Check if tags count is exceeded for all repositories.

    Updates tags_counter that keeps state for the current session.

    """
    image_tags = image_summary.get('RepoTags')
    if max_tags_count is None or no_image_tags(image_tags):
        return False
    exceeds_max_tags_count = True
    for tag in image_tags:
        repo, _, _ = tag.rpartition(':')
        tags_counter[repo] += 1
        if tags_counter[repo] <= max_tags_count:
            exceeds_max_tags_count = False
    return exceeds_max_tags_count


def filter_excluded_images(images, exclude_set):
    def include_image(image_summary):
        image_tags = image_summary.get('RepoTags')
        if no_image_tags(image_tags):
            return True
        for exclude_pattern in exclude_set:
            if fnmatch.filter(image_tags, exclude_pattern):
                return False
        return True

    return filter(include_image, images)


def filter_images_in_use(images, image_tags_in_use):
    def get_tag_set(image_summary):
        image_tags = image_summary.get('RepoTags')
        if no_image_tags(image_tags):
            # The repr of the image Id used by client.containers()
            return {'%s:latest' % image_summary['Id'][:12]}
        return set(image_tags)

    def image_not_in_use(image_summary):
        return not get_tag_set(image_summary) & image_tags_in_use

    return filter(image_not_in_use, images)


def is_image_old(image, min_date):
    return min_date and dateutil.parser.parse(image['Created']) < min_date


def no_image_tags(image_tags):
    return not image_tags or image_tags == ['<none>:<none>']


def remove_image(client, image_summary, min_date,
                 exceeds_max_tags_count, dry_run):
    image = api_call(client.inspect_image, image=image_summary['Id'])
    if not image or not (
            exceeds_max_tags_count or is_image_old(image, min_date)):
        return

    log.info("Removing image %s" % format_image(image, image_summary))
    if dry_run:
        return

    image_tags = image_summary.get('RepoTags')
    # If there are no tags, remove the id
    if no_image_tags(image_tags):
        api_call(client.remove_image, image=image_summary['Id'])
        return

    # Remove any repository tags so we don't hit 409 Conflict
    for image_tag in image_tags:
        api_call(client.remove_image, image=image_tag)


def remove_volume(client, volume, dry_run):
    if not volume:
        return

    log.info("Removing volume %s" % volume['Name'])
    if dry_run:
        return

    api_call(client.remove_volume, name=volume['Name'])


def cleanup_volumes(client, dry_run):
    dangling_volumes = get_dangling_volumes(client)

    for volume in reversed(dangling_volumes):
        log.info("Removing dangling volume %s", volume['Name'])
        remove_volume(client, volume, dry_run)


def api_call(func, **kwargs):
    try:
        return func(**kwargs)
    except requests.exceptions.Timeout as e:
        params = ','.join('%s=%s' % item for item in kwargs.items())
        log.warn("Failed to call %s %s %s" % (func.__name__, params, e))
    except docker.errors.APIError as ae:
        params = ','.join('%s=%s' % item for item in kwargs.items())
        log.warn("Error calling %s %s %s" % (func.__name__, params, ae))


def format_image(image, image_summary):
    def get_tags():
        tags = image_summary.get('RepoTags')
        if not tags or tags == ['<none>:<none>']:
            return ''
        return ', '.join(tags)

    return "%s %s" % (image['Id'][:16], get_tags())


def build_exclude_set(image_tags, exclude_file):
    exclude_set = set(image_tags or [])

    def is_image_tag(line):
        return line and not line.startswith('#')

    if exclude_file:
        lines = [line.strip() for line in exclude_file.read().split('\n')]
        exclude_set.update(filter(is_image_tag, lines))
    return exclude_set


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout)

    args = get_args()
    client = docker.Client(version='auto', timeout=args.timeout)

    if args.max_container_age:
        cleanup_containers(client, args.max_container_age, args.dry_run)

    if args.max_image_age or args.max_tags_count:
        exclude_set = build_exclude_set(
            args.exclude_image,
            args.exclude_image_file)
        cleanup_images(
            client,
            args.max_image_age,
            args.max_tags_count,
            args.dry_run,
            exclude_set)

    if args.dangling_volumes:
        cleanup_volumes(client, args.dry_run)


def get_args(args=None):
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
        help="Maximum age for an image. Images older than this age will be "
             "removed. Age can be specified in any pytimeparse supported "
             "format.")
    parser.add_argument(
        '--max-tags-count',
        type=int,
        help="Maximum number of tags to keep for an image. "
             "Only the most recently added tags are kept.")
    parser.add_argument(
        '--dangling-volumes',
        action="store_true",
        help="Dangling volumes will be removed.")
    parser.add_argument(
        '--dry-run', action="store_true",
        help="Only log actions, don't remove anything.")
    parser.add_argument(
        '-t', '--timeout', type=int, default=60,
        help="HTTP timeout in seconds for making docker API calls.")
    parser.add_argument(
        '--exclude-image',
        action='append',
        help="Never remove images with this tag.")
    parser.add_argument(
        '--exclude-image-file',
        type=argparse.FileType('r'),
        help="Path to a file which contains a list of images to exclude, one "
             "image tag per line.")

    return parser.parse_args(args=args)


if __name__ == "__main__":
    main()
