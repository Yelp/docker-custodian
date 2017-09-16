import datetime

from dateutil import tz
import docker
try:
    from unittest import mock
except ImportError:
    import mock
import pytest


@pytest.fixture
def container():
    return {
        'Id': 'abcdabcdabcdabcd',
        'Created': '2013-12-20T17:00:00Z',
        'Name': '/container_name',
        'Config': {
            'Image': 'docker.io/test/image:1234',
        },
        'State': {
            'Running': False,
            'FinishedAt': '2014-01-01T17:30:00Z',
            'StartedAt': '2014-01-01T17:01:00Z',
        }
    }


@pytest.fixture
def image():
    return {
        'Id': 'abcdabcdabcdabcd',
        'Created': '2014-01-20T05:00:00Z',
    }


@pytest.fixture
def now():
    return datetime.datetime(2014, 1, 20, 10, 10, tzinfo=tz.tzutc())


@pytest.fixture
def earlier_time():
    return datetime.datetime(2014, 1, 1, 0, 0, tzinfo=tz.tzutc())


@pytest.fixture
def later_time():
    return datetime.datetime(2014, 1, 20, 0, 10, tzinfo=tz.tzutc())


@pytest.fixture
def mock_client():
    client = mock.create_autospec(docker.Client)
    client._version = '1.17'
    return client
