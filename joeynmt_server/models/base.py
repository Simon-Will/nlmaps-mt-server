import datetime as dt

from joeynmt_server.app import db
from joeynmt_server.utils.helper import get_utc_now


class BaseModel(db.Model):

    __abstract__ = True

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False
    )

    created = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=get_utc_now
    )

    def sorted_attributes(self) -> list:
        sorted_attributes = sorted(
            (col.name, getattr(self, col.name))
            for col in self.__table__.columns
        )
        return sorted_attributes

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        attributes = ', '.join(f'{a[0]}={a[1]!r}'
                               for a in self.sorted_attributes())
        return '{}({})'.format(class_name, attributes)

    def json_ready_dict(self) -> dict:
        d = {}
        for key, val in self.sorted_attributes():
            if isinstance(val, dt.datetime):
                val = val.isoformat()
            d[key] = val
        return d
