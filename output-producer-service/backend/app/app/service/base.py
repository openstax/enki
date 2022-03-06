from typing import Optional, Any

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session as BaseSession

from app.db.base_class import Base as BaseSchema


class ServiceBase(object):
    def __init__(self, schema_model: BaseSchema, data_model: BaseModel):
        self.schema_model = schema_model
        self.data_model = data_model

    def get(self, db_session: BaseSession, obj_id: int) -> Optional[BaseSchema]:
        return db_session.query(self.schema_model).filter(self.schema_model.id == obj_id).first()

    def get_first_by(self, db_session: BaseSession, **kwargs: Any):
        return db_session.query(self.schema_model).filter_by(**kwargs).first()

    def get_items(self, db_session: BaseSession, *, skip=0, limit=100):
        return db_session.query(self.schema_model).offset(skip).limit(limit).all()

    def get_items_by(self, db_session: BaseSession, *, skip=0, limit=100, **kwargs):
        return db_session.query(self.schema_model).offset(skip).limit(limit).filter_by(
            **kwargs).all()

    def get_items_order_by(self, db_session: BaseSession, *, skip=0, limit=100, order_by=[]):
        return db_session.query(self.schema_model).order_by(*order_by).offset(skip).limit(limit).all()

    def create(self, db_session: BaseSession, obj_in: BaseModel) -> BaseSchema:
        obj_data = jsonable_encoder(obj_in)

        obj = self.schema_model(**obj_data)
        db_session.add(obj)
        db_session.commit()
        return obj

    def update(self, db_session: BaseSession, obj: BaseSchema, obj_in: BaseModel):

        obj_data = obj.to_data_model(self.data_model).dict(skip_defaults=True)
        update_data = obj_in.dict(skip_defaults=True)

        formatted_data = {
            key: value
            for key, value in jsonable_encoder(obj_in).items()
            if key in update_data and key in obj_data
        }

        for field, value in formatted_data.items():
            setattr(obj, field, value)

        db_session.merge(obj)
        db_session.commit()
        return obj

    def delete(self):
        pass
