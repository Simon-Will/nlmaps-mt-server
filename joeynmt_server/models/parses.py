from joeynmt_server.app import db
from joeynmt_server.models.base import BaseModel


class Parse(BaseModel):

    __tablename__ = 'parses'

    __table_args__ = (
        db.UniqueConstraint('nl', 'model', name='unique_nl_model'),
    )

    nl = db.Column(db.Unicode(500), nullable=False)

    lin = db.Column(db.Unicode(500), nullable=False)

    model = db.Column(db.Unicode(500), nullable=False)
