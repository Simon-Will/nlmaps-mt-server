import datetime as dt


def get_utc_now():
    return dt.datetime.now(dt.timezone.utc)
