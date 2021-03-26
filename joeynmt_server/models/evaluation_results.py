from joeynmt_server.app import db
from joeynmt_server.models.base import BaseModel
from joeynmt_server.models.train_usages import TrainUsage


class EvaluationResult(BaseModel):
    __tablename__ = 'evaluation_results'

    label = db.Column(db.Unicode(50), nullable=False)
    model = db.Column(db.Unicode(500), nullable=False)
    correct = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)

    @property
    def accuracy(self):
        return self.correct / self.total


    def json_ready_dict(self) -> dict:
        d = super().json_ready_dict()
        d['accuracy'] = self.accuracy
        return d
