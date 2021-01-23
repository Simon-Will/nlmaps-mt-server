import datetime as dt


def get_utc_now(aware=True):
    if aware:
        return dt.datetime.now(dt.timezone.utc)
    else:
        return dt.datetime.utcnow()
