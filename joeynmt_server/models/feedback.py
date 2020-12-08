from joeynmt_server.app import db
from joeynmt_server.models.base import BaseModel


class Feedback(BaseModel):

    __tablename__ = 'feedback'

    nl = db.Column(db.Unicode(500), nullable=False)

    system_lin = db.Column(db.Unicode(500), nullable=True)

    correct_lin = db.Column(db.Unicode(500), nullable=True)

    model = db.Column(db.Unicode(500), nullable=False)

    user_id = db.Column(db.Integer, nullable=True)

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey('feedback.id'),
        nullable=True,
    )
