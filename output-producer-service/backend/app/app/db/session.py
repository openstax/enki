from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from app.core import config

engine = create_engine(config.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True, convert_unicode=True)

session_factory = sessionmaker(bind=engine)

db_session = scoped_session(session_factory)
Session = session_factory
