from joeynmt_server.app import db
from joeynmt_server.models.base import BaseModel


class TrainUsage(BaseModel):

    __tablename__ = 'train_usages'

    model = db.Column(db.Unicode(500), nullable=False)

    usage_count = db.Column(db.Integer, nullable=False, default=0)

    feedback_id = db.Column(
        db.Integer,
        db.ForeignKey('feedback.id'),
        nullable=False
    )

    feedback = db.relationship('Feedback', back_populates='train_usages')
