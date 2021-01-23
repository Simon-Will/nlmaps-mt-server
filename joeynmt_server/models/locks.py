from joeynmt_server.app import db
from joeynmt_server.models.base import BaseModel


class Lock(BaseModel):

    __tablename__ = 'locks'

    name = db.Column(db.Unicode(100), nullable=False, unique=True)
