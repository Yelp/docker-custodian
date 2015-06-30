import datetime
try:
    from unittest import mock
except ImportError:
    import mock

from dateutil import tz

from docker_custodian import args


def test_datetime_seconds_ago(now):
    expected = datetime.datetime(2014, 1, 15, 10, 10, tzinfo=tz.tzutc())
    with mock.patch(
        'docker_custodian.args.datetime.datetime',
        autospec=True,
    ) as mock_datetime:
        mock_datetime.now.return_value = now
        assert args.datetime_seconds_ago(24 * 60 * 60 * 5) == expected


def test_timedelta_type_none():
    assert args.timedelta_type(None) is None


def test_timedelta_type(now):
    expected = datetime.datetime(2014, 1, 15, 10, 10, tzinfo=tz.tzutc())
    with mock.patch(
        'docker_custodian.args.datetime.datetime',
        autospec=True,
    ) as mock_datetime:
        mock_datetime.now.return_value = now
        assert args.timedelta_type('5 days') == expected
