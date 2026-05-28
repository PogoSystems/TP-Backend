from sqlalchemy.orm import DeclarativeBase
# hereditary class for any Model of the project that makes SQLAlchemy recognize and register each of them in the database
# it is used in the models.py of each module, and it is imported in the env.py of alembic to make the migrations work
class Base(DeclarativeBase):
    pass
