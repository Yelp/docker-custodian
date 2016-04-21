import datetime as dt
from time import sleep

from six import StringIO
import textwrap

import docker.errors
try:
    from unittest import mock
except ImportError:
    import mock
import requests.exceptions

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


def test_filter_images_with_no_event():
    mock_events = [
    ]
    mock_images = [
        {'Id': 'abcd:latest', 'Created': '2014-01-01T01:01:01Z'},
        {'Id': 'abbb:latest', 'Created': '2014-01-01T01:01:01Z'},
    ]
    expected = [
        {'Id': 'abcd:latest', 'Created': '2014-01-01T01:01:01Z'},
        {'Id': 'abbb:latest', 'Created': '2014-01-01T01:01:01Z'},
    ]
    actual = docker_gc.filter_used_images(
        mock_images,
        mock_events
    )
    assert list(actual) == expected


def test_filter_images_with_recent_approved_event():
    mock_events = [
        {
            'Type': 'image',
            'time': 12345,
            'status': 'pull',
            'id': 'abcd:latest',
            'timeNano': 12345,
            'Actor': {
                'Attributes': {'name': 'abcd'},
                'ID': 'abcd:latest'
            },
            'Action': 'pull'
        }
    ]
    mock_images = [
        {'Id': 'abcd:latest', 'Created': '2014-01-01T01:01:01Z'},
        {'Id': 'abbb:latest', 'Created': '2014-01-01T01:01:01Z'},
    ]
    expected = [
        {'Id': 'abbb:latest', 'Created': '2014-01-01T01:01:01Z'},
    ]
    actual = docker_gc.filter_used_images(
        mock_images,
        mock_events
    )
    assert list(actual) == expected


def test_filter_images_with_recent_unapproved_event():
    mock_events = [
        {
            'Type': 'image',
            'time': 12345,
            'status': 'blah',
            'id': 'abcd:latest',
            'timeNano': 12345,
            'Actor': {
                'Attributes': {'name': 'abcd'},
                'ID': 'abcd:latest'
            },
            'Action': 'blah'
        }
    ]
    mock_images = [
        {'Id': 'abcd:latest', 'Created': '2014-01-01T01:01:01Z'},
        {'Id': 'abbb:latest', 'Created': '2014-01-01T01:01:01Z'},
    ]
    expected = [
        {'Id': 'abcd:latest', 'Created': '2014-01-01T01:01:01Z'},
        {'Id': 'abbb:latest', 'Created': '2014-01-01T01:01:01Z'},
    ]
    actual = docker_gc.filter_used_images(
        mock_images,
        mock_events
    )
    assert list(actual) == expected


def test_list_events_since_with_date():
    client = docker.Client(version='auto', timeout=10)

    # assert no busybox event before pull
    seconds = 2
    since = dt.timedelta(seconds=seconds)
    events = docker_gc.list_events_since(client, since)
    busybox = [
        event for event in events
        if 'busybox' in event['Actor']['Attributes']['name']
    ]
    assert not busybox

    client.pull('busybox:latest')

    # assert busybox event after pull
    events = docker_gc.list_events_since(client, since)
    busybox = [
        event for event in events
        if 'busybox:latest' == event['Actor']['ID']
    ]
    assert len(busybox) == 1
    assert busybox[0]['Type'] == 'image'
    assert busybox[0]['Action'] == 'pull'

    # assert busybox event was in the time window
    now = dt.datetime.utcnow()
    event_time = dt.datetime.utcfromtimestamp(busybox[0]['time'])
    assert now - since <= event_time <= now

    sleep(1)

    # assert list_events_since respects `since`
    since = dt.timedelta(seconds=0)
    events = docker_gc.list_events_since(client, since)
    assert events == []


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
    mock_client.remove_container.assert_called_once_with('abcd')


def test_cleanup_images(mock_client, now):
    max_image_age = now
    since = None
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

    docker_gc.cleanup_images(mock_client, max_image_age, since, False, set())
    assert mock_client.remove_image.mock_calls == [
        mock.call(image['Id']) for image in reversed(images)
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


def test_remove_image_no_tags(mock_client, image, now):
    image_id = 'abcd'
    image_summary = {'Id': image_id}
    mock_client.inspect_image.return_value = image
    docker_gc.remove_image(mock_client, image_summary, False)

    mock_client.remove_image.assert_called_once_with(image_id)


def test_cleanup_image_new_image_not_removed(
        mock_client,
        image,
        later_time
):
    max_image_age = later_time
    since = None
    mock_client.inspect_image.return_value = image
    docker_gc.cleanup_images(mock_client, max_image_age, since, False, set())

    assert not mock_client.remove_image.mock_calls


def test_remove_image_with_tags(mock_client, image, now):
    image_id = 'abcd'
    repo_tags = ['user/one:latest', 'user/one:12345']
    image_summary = {
            'Id': image_id,
            'RepoTags': repo_tags
    }
    mock_client.inspect_image.return_value = image
    docker_gc.remove_image(mock_client, image_summary, False)

    assert mock_client.remove_image.mock_calls == [
        mock.call(tag) for tag in repo_tags
    ]


def test_api_call_success():
    func = mock.Mock()
    id = "abcd"
    result = docker_gc.api_call(func, id)
    func.assert_called_once_with(id)
    assert result == func.return_value


def test_api_call_with_timeout():
    func = mock.Mock(
        side_effect=requests.exceptions.ReadTimeout("msg"),
        __name__="remove_image")
    id = "abcd"

    with mock.patch(
            'docker_custodian.docker_gc.log',
            autospec=True) as mock_log:
        docker_gc.api_call(func, id)

    func.assert_called_once_with(id)
    mock_log.warn.assert_called_once_with(
        'Failed to call remove_image abcd msg'
    )


def test_api_call_with_api_error():
    func = mock.Mock(
        side_effect=docker.errors.APIError(
            "Ooops",
            mock.Mock(status_code=409, reason="Conflict"),
            explanation="failed"),
        __name__="remove_image")
    id = "abcd"

    with mock.patch(
            'docker_custodian.docker_gc.log',
            autospec=True) as mock_log:
        docker_gc.api_call(func, id)

    func.assert_called_once_with(id)
    mock_log.warn.assert_called_once_with(
        'Error calling remove_image abcd '
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
                max_image_recently_used=dt.timedelta(seconds=2),
                exclude_image=[],
                exclude_image_file=None,
            )
            docker_gc.main()
