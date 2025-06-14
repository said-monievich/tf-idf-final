from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Path, APIRouter, status
from models import Document, User
from database import SessionLocal
from starlette import status
from pydantic import BaseModel, Field
from .auth import get_current_user
from passlib.context import CryptContext

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[User, Depends(get_current_user)]
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserVerification(BaseModel):
    password: str
    new_password: str = Field(min_length=6)



#Показать информацию о текущем пользователе
# noinspection PyTypeChecker
@router.get("/", status_code=status.HTTP_200_OK)
async def get_user(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication failed")
    return db.query(User).filter(user.id == User.id).first()


#PATCH /user/<user_id> — изменение пароля, переданного в теле запроса;
@router.put("/change/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(user: user_dependency, db: db_dependency, user_verification: UserVerification):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication failed")
    user_model = db.query(User).filter(user.id == User.id).first()

    if not bcrypt_context.verify(user_verification.password, user_model.hashed_password):
        raise HTTPException(status_code=404, detail="Error on password change")
    user_model.hashed_password = bcrypt_context.hash(user_verification.new_password)
    db.add(user_model)
    db.commit()


#DELETE /user/<user_id> — удаление пользователя
@router.delete("/delete/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    db: db_dependency,
    current_user: Annotated[User, Depends(get_current_user)]
):
    user_in_session = db.query(User).filter(User.id == current_user.id).first()
    if user_in_session is None:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user_in_session)
    db.commit()










