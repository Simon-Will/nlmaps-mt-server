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

    @classmethod
    def get_or_create(cls, nl, model, lin=''):
        parse = cls.query.filter_by(nl=nl, model=model).first()
        if not parse:
            parse = cls(nl=nl, model=model, lin=lin)
            db.session.add(parse)
            db.session.commit()
        return parse
