import datetime
import sqlalchemy
from data.db_session import SqlAlchemyBase


class Remind(SqlAlchemyBase):
    __tablename__ = 'remminds'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    r_type = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    day = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    time = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    text = sqlalchemy.Column(sqlalchemy.String, unique=False, nullable=True)
    userid = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    channel = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    guild = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    reps = sqlalchemy.Column(sqlalchemy.Integer)