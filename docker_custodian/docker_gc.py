#!/usr/bin/env python
"""
Remove old docker containers and images that are no longer in use.

"""
import argparse
import fnmatch
import logging
import sys

import dateutil.parser
import docker
import docker.errors
import requests.exceptions

from collections import namedtuple
from docker_custodian.args import timedelta_type
from docker.utils import kwargs_from_env

log = logging.getLogger(__name__)


# This seems to be something docker uses for a null/zero date
YEAR_ZERO = "0001-01-01T00:00:00Z"

ExcludeLabel = namedtuple('ExcludeLabel', ['key', 'value'])


def cleanup_containers(
    client,
    max_container_age,
    dry_run,
    exclude_container_labels,
):
    all_containers = get_all_containers(client)
    filtered_containers = filter_excluded_containers(
        all_containers,
        exclude_container_labels,
    )
    for container_summary in reversed(list(filtered_containers)):
        container = api_call(
            client.inspect_container,
            container=container_summary['Id'],
        )
        if not container or not should_remove_container(
            container,
            max_container_age,
        ):
            continue

        log.info("Removing container %s %s %s" % (
            container['Id'][:16],
            container.get('Name', '').lstrip('/'),
            container['State']['FinishedAt']))

        if not dry_run:
            api_call(
                client.remove_container,
                container=container['Id'],
                v=True,
            )


def filter_excluded_containers(containers, exclude_container_labels):
    if not exclude_container_labels:
        return containers

    def include_container(container):
        if should_exclude_container_with_labels(
            container,
            exclude_container_labels,
        ):
            return False
        return True
    return filter(include_container, containers)


def should_exclude_container_with_labels(container, exclude_container_labels):
    if container['Labels']:
        for exclude_label in exclude_container_labels:
            if exclude_label.value:
                matching_keys = fnmatch.filter(
                    container['Labels'].keys(),
                    exclude_label.key,
                )
                label_values_to_check = [
                    container['Labels'][matching_key]
                    for matching_key in matching_keys
                ]
                if fnmatch.filter(label_values_to_check, exclude_label.value):
                    return True
            else:
                if fnmatch.filter(
                    container['Labels'].keys(),
                    exclude_label.key
                ):
                    return True
    return False


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
    volumes = client.volumes({'dangling': True})['Volumes'] or []
    log.info("Found %s dangling volumes", len(volumes))
    return volumes


def cleanup_images(client, max_image_age, dry_run, exclude_set):
    # re-fetch container list so that we don't include removed containers

    containers = get_all_containers(client)
    images = get_all_images(client)
    if docker.utils.compare_version('1.21', client._version) < 0:
        image_tags_in_use = {container['Image'] for container in containers}
        images = filter_images_in_use(images, image_tags_in_use)
    else:
        # ImageID field was added in 1.21
        image_ids_in_use = {container['ImageID'] for container in containers}
        images = filter_images_in_use_by_id(images, image_ids_in_use)
    images = filter_excluded_images(images, exclude_set)

    for image_summary in reversed(list(images)):
        remove_image(client, image_summary, max_image_age, dry_run)


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
            return set(['%s:latest' % image_summary['Id'][:12]])
        return set(image_tags)

    def image_not_in_use(image_summary):
        return not get_tag_set(image_summary) & image_tags_in_use

    return filter(image_not_in_use, images)


def filter_images_in_use_by_id(images, image_ids_in_use):
    def image_not_in_use(image_summary):
        return image_summary['Id'] not in image_ids_in_use

    return filter(image_not_in_use, images)


def is_image_old(image, min_date):
    return dateutil.parser.parse(image['Created']) < min_date


def no_image_tags(image_tags):
    return not image_tags or image_tags == ['<none>:<none>']


def remove_image(client, image_summary, min_date, dry_run):
    image = api_call(client.inspect_image, image=image_summary['Id'])
    if not image or not is_image_old(image, min_date):
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


def format_exclude_labels(exclude_label_args):
    exclude_labels = []
    for exclude_label_arg in exclude_label_args:
        split_exclude_label = exclude_label_arg.split('=', 1)
        exclude_label_key = split_exclude_label[0]
        if len(split_exclude_label) == 2:
            exclude_label_value = split_exclude_label[1]
        else:
            exclude_label_value = None
        exclude_labels.append(
            ExcludeLabel(
                key=exclude_label_key,
                value=exclude_label_value,
            )
        )
    return exclude_labels


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout)

    args = get_args()
    client = docker.APIClient(version='auto',
                              timeout=args.timeout,
                              **kwargs_from_env())

    exclude_container_labels = format_exclude_labels(
        args.exclude_container_label
    )

    if args.max_container_age:
        cleanup_containers(
            client,
            args.max_container_age,
            args.dry_run,
            exclude_container_labels,
        )

    if args.max_image_age:
        exclude_set = build_exclude_set(
            args.exclude_image,
            args.exclude_image_file)
        cleanup_images(client, args.max_image_age, args.dry_run, exclude_set)

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
        help="Maxium age for an image. Images older than this age will be "
             "removed. Age can be specified in any pytimeparse supported "
             "format.")
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
    parser.add_argument(
        '--exclude-container-label',
        action='append', type=str, default=[],
        help="Never remove containers with this label key or label key=value")

    return parser.parse_args(args=args)


if __name__ == "__main__":
    main()
