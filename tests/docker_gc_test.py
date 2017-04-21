import datetime

from dateutil import tz
from six import StringIO
import textwrap

import docker.errors
try:
    from unittest import mock
except ImportError:
    import mock
import requests.exceptions
import pytest

from docker_custodian import docker_gc


class TestShouldRemoveContainer(object):

    def test_is_running(self, container, now):
        container['State']['Running'] = True
        assert not docker_gc.should_remove_container(container, now)

    def test_is_ghost(self, container, now):
        container['State']['Ghost'] = True
        assert docker_gc.should_remove_container(container, now)

    def test_old_never_run(self, container, now, earlier_time):
        container['Created'] = str(earlier_time)
        container['State']['FinishedAt'] = docker_gc.YEAR_ZERO
        assert docker_gc.should_remove_container(container, now)

    def test_not_old_never_run(self, container, now, earlier_time):
        container['Created'] = str(now)
        container['State']['FinishedAt'] = docker_gc.YEAR_ZERO
        assert not docker_gc.should_remove_container(container, now)

    def test_old_stopped(self, container, now):
        assert docker_gc.should_remove_container(container, now)

    def test_not_old(self, container, now):
        container['State']['FinishedAt'] = '2014-01-21T00:00:00Z'
        assert not docker_gc.should_remove_container(container, now)


def test_cleanup_containers(mock_client, now):
    max_container_age = now
    mock_client.containers.return_value = [
        {'Id': 'abcd'},
        {'Id': 'abbb'},
    ]
    mock_containers = [
        {
            'Id': 'abcd',
            'Name': 'one',
            'State': {
                'Running': False,
                'FinishedAt': '2014-01-01T01:01:01Z'
            }
        },
        {
            'Id': 'abbb',
            'Name': 'two',
            'State': {
                'Running': True,
                'FinishedAt': '2014-01-01T01:01:01Z'
            }
        }
    ]
    mock_client.inspect_container.side_effect = iter(mock_containers)
    docker_gc.cleanup_containers(mock_client, max_container_age, False)
    mock_client.remove_container.assert_called_once_with(container='abcd',
                                                         v=True)


def test_cleanup_images(mock_client, now):
    max_image_age = now
    mock_client.images.return_value = images = [
        {'Id': 'abcd'},
        {'Id': 'abbb'},
    ]
    mock_images = [
        {
            'Id': 'abcd',
            'Created': '2014-01-01T01:01:01Z'
        },
        {
            'Id': 'abbb',
            'Created': '2014-01-01T01:01:01Z'
        },
    ]
    mock_client.inspect_image.side_effect = iter(mock_images)

    docker_gc.cleanup_images(
        mock_client, max_image_age, None, False, set())
    assert mock_client.remove_image.mock_calls == [
        mock.call(image=image['Id']) for image in images
    ]


@pytest.mark.parametrize('max_image_age,expected_remove_calls', [
    # First two cases image 'abce' cannot be removed because it has tag
    # that points to repository 'user/two' for the first time.
    (
        None,
        [mock.call(image=i) for i in ['user/two:aaaa', 'user/one:bbbb']]
    ),
    (
        datetime.datetime(2014, 1, 1, 0, 0, tzinfo=tz.tzutc()),
        [mock.call(image=i) for i in ['user/two:aaaa', 'user/one:bbbb']]
    ),
    # All images should be removed because max_image_age is greater than
    # the age of all images.
    (
        datetime.datetime(2014, 2, 1, 0, 0, tzinfo=tz.tzutc()),
        [mock.call(image=i) for i in ['user/one:latest', 'user/one:abcd',
                                      'user/two:latest', 'user/one:efgh',
                                      'user/two:aaaa', 'user/one:bbbb']]
    ),
])
def test_cleanup_images_max_tags_count(mock_client,
                                       max_image_age, expected_remove_calls):
    mock_client.images.return_value = [
        {'Id': 'abcd', 'RepoTags': ['user/one:latest', 'user/one:abcd']},
        {'Id': 'abce', 'RepoTags': ['user/two:latest', 'user/one:efgh']},
        {'Id': 'abcf', 'RepoTags': ['user/two:aaaa', 'user/one:bbbb']},
    ]
    mock_images = [
        {
            'Id': 'abcd',
            'Created': '2014-01-01T01:01:01Z'
        },
        {
            'Id': 'abce',
            'Created': '2014-01-01T01:01:01Z'
        },
        {
            'Id': 'abcf',
            'Created': '2014-01-01T01:01:01Z'
        },
    ]
    mock_client.inspect_image.side_effect = iter(mock_images)
    max_tags_count = 1
    docker_gc.cleanup_images(
        mock_client, max_image_age, max_tags_count, False, set())
    # Keep at least max_tags_count tags for each repository.
    assert mock_client.remove_image.mock_calls == expected_remove_calls


def test_cleanup_volumes(mock_client):
    mock_client.volumes.return_value = volumes = {
        'Volumes': [
            {
                'Mountpoint': 'unused',
                'Labels': None,
                'Driver': 'unused',
                'Name': u'one'
            },
            {
                'Mountpoint': 'unused',
                'Labels': None,
                'Driver': 'unused',
                'Name': u'two'
            },
        ],
        'Warnings': None,
    }

    docker_gc.cleanup_volumes(mock_client, False)
    assert mock_client.remove_volume.mock_calls == [
        mock.call(name=volume['Name'])
        for volume in reversed(volumes['Volumes'])
    ]


def test_filter_images_in_use():
    image_tags_in_use = set([
        'user/one:latest',
        'user/foo:latest',
        'other:12345',
        '2471708c19be:latest',
    ])
    images = [
        {
            'RepoTags': ['<none>:<none>'],
            'Id': '2471708c19beabababab'
        },
        {
            'RepoTags': ['<none>:<none>'],
            'Id': 'babababababaabababab'
        },
        {
            'RepoTags': ['user/one:latest', 'user/one:abcd']
        },
        {
            'RepoTags': ['other:abcda']
        },
        {
            'RepoTags': ['other:12345']
        },
        {
            'RepoTags': ['new_image:latest', 'new_image:123']
        },
    ]
    expected = [
        {
            'RepoTags': ['<none>:<none>'],
            'Id': 'babababababaabababab'
        },
        {
            'RepoTags': ['other:abcda']
        },
        {
            'RepoTags': ['new_image:latest', 'new_image:123']
        },
    ]
    actual = docker_gc.filter_images_in_use(images, image_tags_in_use)
    assert list(actual) == expected


def test_filter_excluded_images():
    exclude_set = set([
        'user/one:latest',
        'user/foo:latest',
        'other:12345',
    ])
    images = [
            {
                'RepoTags': ['<none>:<none>'],
                'Id': 'babababababaabababab'
            },
            {
                'RepoTags': ['user/one:latest', 'user/one:abcd']
            },
            {
                'RepoTags': ['other:abcda']
            },
            {
                'RepoTags': ['other:12345']
            },
            {
                'RepoTags': ['new_image:latest', 'new_image:123']
            },
    ]
    expected = [
            {
                'RepoTags': ['<none>:<none>'],
                'Id': 'babababababaabababab'
            },
            {
                'RepoTags': ['other:abcda']
            },
            {
                'RepoTags': ['new_image:latest', 'new_image:123']
            },
    ]
    actual = docker_gc.filter_excluded_images(images, exclude_set)
    assert list(actual) == expected


def test_filter_excluded_images_advanced():
    exclude_set = set([
        'user/one:*',
        'user/foo:tag*',
        'user/repo-*:tag',
    ])
    images = [
            {
                'RepoTags': ['<none>:<none>'],
                'Id': 'babababababaabababab'
            },
            {
                'RepoTags': ['user/one:latest', 'user/one:abcd']
            },
            {
                'RepoTags': ['user/foo:test']
            },
            {
                'RepoTags': ['user/foo:tag123']
            },
            {
                'RepoTags': ['user/repo-1:tag']
            },
            {
                'RepoTags': ['user/repo-2:tag']
            },

    ]
    expected = [
            {
                'RepoTags': ['<none>:<none>'],
                'Id': 'babababababaabababab'
            },
            {
                'RepoTags': ['user/foo:test'],
            },
    ]
    actual = docker_gc.filter_excluded_images(images, exclude_set)
    assert list(actual) == expected


def test_is_image_old(image, now):
    assert docker_gc.is_image_old(image, now)


def test_is_image_old_false(image, later_time):
    assert not docker_gc.is_image_old(image, later_time)


def test_is_image_old_none(image, later_time):
    assert not docker_gc.is_image_old(image, None)


def test_remove_image_no_tags(mock_client, image, now):
    image_id = 'abcd'
    image_summary = {'Id': image_id}
    mock_client.inspect_image.return_value = image
    docker_gc.remove_image(mock_client, image_summary, now, False, False)

    mock_client.remove_image.assert_called_once_with(image=image_id)


def test_remove_image_new_image_not_removed(mock_client, image, later_time):
    image_id = 'abcd'
    image_summary = {'Id': image_id}
    mock_client.inspect_image.return_value = image
    docker_gc.remove_image(
        mock_client, image_summary, later_time, False, False)

    assert not mock_client.remove_image.mock_calls


def test_remove_image_with_tags(mock_client, image, now):
    image_id = 'abcd'
    repo_tags = ['user/one:latest', 'user/one:12345']
    image_summary = {
            'Id': image_id,
            'RepoTags': repo_tags
    }
    mock_client.inspect_image.return_value = image
    docker_gc.remove_image(mock_client, image_summary, now, False, False)

    assert mock_client.remove_image.mock_calls == [
        mock.call(image=tag) for tag in repo_tags
    ]


def test_remove_image_exceeds_max_tag_count(mock_client, image, now):
    image_id = 'abcd'
    repo_tags = ['user/one:latest', 'user/one:12345']
    image_summary = {
        'Id': image_id,
        'RepoTags': repo_tags
    }
    mock_client.inspect_image.return_value = image
    docker_gc.remove_image(mock_client, image_summary, None, True, False)

    assert mock_client.remove_image.mock_calls == [
        mock.call(image=tag) for tag in repo_tags
    ]


def test_api_call_success():
    func = mock.Mock()
    container = "abcd"
    result = docker_gc.api_call(func, container=container)
    func.assert_called_once_with(container="abcd")
    assert result == func.return_value


def test_api_call_with_timeout():
    func = mock.Mock(
        side_effect=requests.exceptions.ReadTimeout("msg"),
        __name__="remove_image")
    image = "abcd"

    with mock.patch(
            'docker_custodian.docker_gc.log',
            autospec=True) as mock_log:
        docker_gc.api_call(func, image=image)

    func.assert_called_once_with(image="abcd")
    mock_log.warn.assert_called_once_with('Failed to call remove_image '
                                          + 'image=abcd msg'
                                          )


def test_api_call_with_api_error():
    func = mock.Mock(
        side_effect=docker.errors.APIError(
            "Ooops",
            mock.Mock(status_code=409, reason="Conflict"),
            explanation="failed"),
        __name__="remove_image")
    image = "abcd"

    with mock.patch(
            'docker_custodian.docker_gc.log',
            autospec=True) as mock_log:
        docker_gc.api_call(func, image=image)

    func.assert_called_once_with(image="abcd")
    mock_log.warn.assert_called_once_with(
        'Error calling remove_image image=abcd '
        '409 Client Error: Conflict ("failed")')


def days_as_seconds(num):
    return num * 60 * 60 * 24


def test_get_args_with_defaults():
    opts = docker_gc.get_args(args=[])
    assert opts.timeout == 60
    assert opts.dry_run is False
    assert opts.max_container_age is None
    assert opts.max_image_age is None


def test_get_args_with_args():
    with mock.patch(
        'docker_custodian.docker_gc.timedelta_type',
        autospec=True
    ) as mock_timedelta_type:
        opts = docker_gc.get_args(args=[
            '--max-image-age', '30 days',
            '--max-container-age', '3d',
        ])
    assert mock_timedelta_type.mock_calls == [
        mock.call('30 days'),
        mock.call('3d'),
    ]
    assert opts.max_container_age == mock_timedelta_type.return_value
    assert opts.max_image_age == mock_timedelta_type.return_value


def test_get_all_containers(mock_client):
    count = 10
    mock_client.containers.return_value = [mock.Mock() for _ in range(count)]
    with mock.patch('docker_custodian.docker_gc.log',
                    autospec=True) as mock_log:
        containers = docker_gc.get_all_containers(mock_client)
    assert containers == mock_client.containers.return_value
    mock_client.containers.assert_called_once_with(all=True)
    mock_log.info.assert_called_with("Found %s containers", count)


def test_get_all_images(mock_client):
    count = 7
    mock_client.images.return_value = [mock.Mock() for _ in range(count)]
    with mock.patch('docker_custodian.docker_gc.log',
                    autospec=True) as mock_log:
        images = docker_gc.get_all_images(mock_client)
    assert images == mock_client.images.return_value
    mock_log.info.assert_called_with("Found %s images", count)


def test_get_dangling_volumes(mock_client):
    count = 4
    mock_client.volumes.return_value = {
        'Volumes': [mock.Mock() for _ in range(count)]
    }
    with mock.patch('docker_custodian.docker_gc.log',
                    autospec=True) as mock_log:
        volumes = docker_gc.get_dangling_volumes(mock_client)
    assert volumes == mock_client.volumes.return_value['Volumes']
    mock_log.info.assert_called_with("Found %s dangling volumes", count)


def test_build_exclude_set():
    image_tags = [
        'some_image:latest',
        'repo/foo:12345',
        'duplicate:latest',
    ]
    exclude_image_file = StringIO(textwrap.dedent("""
        # Exclude this one because
        duplicate:latest
        # Also this one
        repo/bar:abab
    """))
    expected = set([
        'some_image:latest',
        'repo/foo:12345',
        'duplicate:latest',
        'repo/bar:abab',
    ])

    exclude_set = docker_gc.build_exclude_set(image_tags, exclude_image_file)
    assert exclude_set == expected


def test_build_exclude_set_empty():
    exclude_set = docker_gc.build_exclude_set(None, None)
    assert exclude_set == set()


def test_main(mock_client):
    with mock.patch(
            'docker_custodian.docker_gc.docker.Client',
            return_value=mock_client):

        with mock.patch(
                'docker_custodian.docker_gc.get_args',
                autospec=True) as mock_get_args:
            mock_get_args.return_value = mock.Mock(
                max_image_age=100,
                max_container_age=200,
                exclude_image=[],
                exclude_image_file=None,
            )
            docker_gc.main()
