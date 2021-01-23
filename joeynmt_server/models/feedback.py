from joeynmt_server.app import db
from joeynmt_server.models.base import BaseModel
from joeynmt_server.models.train_usages import TrainUsage


class Feedback(BaseModel):

    __tablename__ = 'feedback'

    nl = db.Column(db.Unicode(500), nullable=False)

    system_lin = db.Column(db.Unicode(500), nullable=False)

    correct_lin = db.Column(db.Unicode(500), nullable=False)

    model = db.Column(db.Unicode(500), nullable=False)

    user_id = db.Column(db.Integer, nullable=True)

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey('feedback.id'),
        nullable=True,
    )

    train_usages = db.relationship('TrainUsage', back_populates='feedback',
                                   cascade='all, delete-orphan')

    def get_usage_for_model(self, model):
        usages = [usage for usage in self.train_usages if usage.model == model]
        if usages:
            return usages[0]
        return None

    def get_usage_count_for_model(self, model):
        usage = self.get_usage_for_model(model)
        if usage:
            return usage.usage_count
        return 0

    def increment_usage_count_for_model(self, model, amount=1):
        usage = self.get_usage_for_model(model)
        if not usage:
            usage = TrainUsage(feedback_id=self.id, model=model, usage_count=0)

        usage.usage_count += amount
        db.session.add(usage)
        db.session.commit()
        return usage.usage_count
