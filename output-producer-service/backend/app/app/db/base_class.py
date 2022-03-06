import re

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.declarative import declarative_base, declared_attr


class CustomBase(object):
    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls):
        def convert(name):
            s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
            return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

        return convert(cls.__name__)

    def to_data_model(self, schema_cls):
        return schema_cls(**self.__dict__)

    @classmethod
    def from_data_model(cls, schema_obj):
        return cls(**jsonable_encoder(schema_obj))


Base = declarative_base(cls=CustomBase)
