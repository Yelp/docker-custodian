try:
    from unittest import mock
except ImportError:
    import mock

from docker_custodian.docker_autostop import (
    build_container_matcher,
    get_opts,
    has_been_running_since,
    main,
    stop_container,
    stop_containers,
)


def test_stop_containers(mock_client, container, now):
    matcher = mock.Mock()
    mock_client.containers.return_value = [container]
    mock_client.inspect_container.return_value = container

    stop_containers(mock_client, now, matcher, False)
    matcher.assert_called_once_with('container_name')
    mock_client.stop.assert_called_once_with(container['Id'])


def test_stop_container(mock_client):
    id = 'asdb'
    stop_container(mock_client, id)
    mock_client.stop.assert_called_once_with(id)


def test_build_container_matcher():
    prefixes = ['one_', 'two_']
    matcher = build_container_matcher(prefixes)

    assert matcher('one_container')
    assert matcher('two_container')
    assert not matcher('three_container')
    assert not matcher('one')


def test_has_been_running_since_true(container, later_time):
    assert has_been_running_since(container, later_time)


def test_has_been_running_since_false(container, earlier_time):
    assert not has_been_running_since(container, earlier_time)


@mock.patch('docker_custodian.docker_autostop.build_container_matcher',
            autospec=True)
@mock.patch('docker_custodian.docker_autostop.stop_containers',
            autospec=True)
@mock.patch('docker_custodian.docker_autostop.get_opts',
            autospec=True)
@mock.patch('docker_custodian.docker_autostop.docker', autospec=True)
def test_main(
        mock_docker,
        mock_get_opts,
        mock_stop_containers,
        mock_build_matcher
):
    mock_get_opts.return_value.timeout = 30
    main()
    mock_get_opts.assert_called_once_with()
    mock_build_matcher.assert_called_once_with(
        mock_get_opts.return_value.prefix)
    mock_stop_containers.assert_called_once_with(
        mock.ANY,
        mock_get_opts.return_value.max_run_time,
        mock_build_matcher.return_value,
        mock_get_opts.return_value.dry_run)


def test_get_opts_with_defaults():
    opts = get_opts(args=['--prefix', 'one', '--prefix', 'two'])
    assert opts.timeout == 60
    assert opts.dry_run is False
    assert opts.prefix == ['one', 'two']
    assert opts.max_run_time is None


def test_get_opts_with_args(now):
    with mock.patch(
        'docker_custodian.docker_autostop.timedelta_type',
        autospec=True
    ) as mock_timedelta_type:
        opts = get_opts(args=['--prefix', 'one', '--max-run-time', '24h'])
    assert opts.max_run_time == mock_timedelta_type.return_value
    mock_timedelta_type.assert_called_once_with('24h')
