import datetime

from dateutil import tz
from pytimeparse import timeparse


def timedelta_type(value):
    """Return the :class:`datetime.datetime.DateTime` for a time in the past.

    :param value: a string containing a time format supported by
    mod:`pytimeparse`
    """
    if value is None:
        return None
    return datetime_seconds_ago(timeparse.timeparse(value))


def datetime_seconds_ago(seconds):
    now = datetime.datetime.now(tz.tzutc())
    return now - datetime.timedelta(seconds=seconds)
