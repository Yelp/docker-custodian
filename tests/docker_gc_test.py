import docker.errors
try:
    from unittest import mock
except ImportError:
    import mock
import requests.exceptions

from docker_custodian import docker_gc


class TestIsOldContainer(object):

    def test_is_running(self, container, now):
        container['State']['Running'] = True
        assert not docker_gc.is_container_old(container, now)

    def test_is_ghost(self, container, now):
        container['State']['Ghost'] = True
        assert docker_gc.is_container_old(container, now)

    def test_old_never_run(self, container, now):
        container['State']['FinishedAt'] = docker_gc.YEAR_ZERO
        assert docker_gc.is_container_old(container, now)

    def test_old_stopped(self, container, now):
        assert docker_gc.is_container_old(container, now)

    def test_not_old(self, container, now):
        container['State']['FinishedAt'] = '2014-01-21T00:00:00Z'
        assert not docker_gc.is_container_old(container, now)


def test_cleanup_containers(mock_client, now):
    max_container_age = now
    mock_client.containers.return_value = [
        dict(Id='abcd'),
        dict(Id='abbb'),
    ]
    mock_containers = [
        dict(
            Id='abcd',
            Name='one',
            State=dict(Running=False, FinishedAt='2014-01-01T01:01:01Z')),
        dict(
            Id='abbb',
            Name='two',
            State=dict(Running=True, FinishedAt='2014-01-01T01:01:01Z'))
    ]
    mock_client.inspect_container.side_effect = iter(mock_containers)
    docker_gc.cleanup_containers(mock_client, max_container_age, False)
    mock_client.remove_container.assert_called_once_with('abcd')


def test_cleanup_images(mock_client, now):
    max_image_age = now
    mock_client.images.return_value = images = [
        dict(Id='abcd'),
        dict(Id='abbb'),
    ]
    mock_images = [
        dict(Id='abcd', Created='2014-01-01T01:01:01Z'),
        dict(Id='abbb', Created='2014-01-01T01:01:01Z'),
    ]
    mock_client.inspect_image.side_effect = iter(mock_images)

    docker_gc.cleanup_images(mock_client, max_image_age, False)
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
        dict(RepoTags=['<none>:<none>'], Id='2471708c19beabababab'),
        dict(RepoTags=['<none>:<none>'], Id='babababababaabababab'),
        dict(RepoTags=['user/one:latest', 'user/one:abcd']),
        dict(RepoTags=['other:abcda']),
        dict(RepoTags=['other:12345']),
        dict(RepoTags=['new_image:latest', 'new_image:123']),
    ]
    expected = [
        dict(RepoTags=['<none>:<none>'], Id='babababababaabababab'),
        dict(RepoTags=['other:abcda']),
        dict(RepoTags=['new_image:latest', 'new_image:123']),
    ]
    actual = docker_gc.filter_images_in_use(images, image_tags_in_use)
    assert actual == expected


def test_is_image_old(image, now):
    assert docker_gc.is_image_old(image, now)


def test_is_image_old_false(image, later_time):
    assert not docker_gc.is_image_old(image, later_time)


def test_remove_image_no_tags(mock_client, image, now):
    image_id = 'abcd'
    image_summary = dict(Id=image_id)
    mock_client.inspect_image.return_value = image
    docker_gc.remove_image(mock_client, image_summary, now, False)

    mock_client.remove_image.assert_called_once_with(image_id)


def test_remove_image_new_image_not_removed(mock_client, image, later_time):
    image_id = 'abcd'
    image_summary = dict(Id=image_id)
    mock_client.inspect_image.return_value = image
    docker_gc.remove_image(mock_client, image_summary, later_time, False)

    assert not mock_client.remove_image.mock_calls


def test_remove_image_with_tags(mock_client, image, now):
    image_id = 'abcd'
    repo_tags = ['user/one:latest', 'user/one:12345']
    image_summary = dict(Id=image_id, RepoTags=repo_tags)
    mock_client.inspect_image.return_value = image
    docker_gc.remove_image(mock_client, image_summary, now, False)

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
    mock_log.warn.assert_called_once_with('Failed to call remove_image abcd msg')


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


def test_get_opts_with_defaults():
    opts = docker_gc.get_opts(args=[])
    assert opts.timeout == 60
    assert opts.dry_run is False
    assert opts.max_container_age is None
    assert opts.max_image_age is None


def test_get_opts_with_args():
    with mock.patch(
        'docker_custodian.docker_gc.timedelta_type',
        autospec=True
    ) as mock_timedelta_type:
        opts = docker_gc.get_opts(args=[
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


def test_main(mock_client):
    with mock.patch(
            'docker_custodian.docker_gc.docker.Client',
            return_value=mock_client):

        with mock.patch(
                'docker_custodian.docker_gc.get_opts',
                autospec=True) as mock_get_opts:
            mock_get_opts.return_value = mock.Mock(
                max_image_age=100,
                max_container_age=200,
            )
            docker_gc.main()
