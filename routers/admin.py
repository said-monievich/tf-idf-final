from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Path, APIRouter
from models import Document, User
from database import SessionLocal
from starlette import status
from pydantic import BaseModel, Field
from .auth import get_current_user

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[User, Depends(get_current_user)]

#Если пользователь == админ -> показать все загруженные файлы
@router.get("/document", status_code=status.HTTP_200_OK)
async def read_all(user: user_dependency, db: db_dependency):
    if user is None or user.role != "admin":
        raise HTTPException(status_code=401, detail="Authentication failed")
    return db.query(Document).all()


#Если пользователь == админ -> удалить документ по id
@router.delete("/document/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(user: user_dependency, db: db_dependency, document_id: int = Path(gt=0)):
    if user is None or user.role != "admin":
        raise HTTPException(status_code=401, detail="Authentication failed")
    document_model = db.query(Document).filter(document_id == Document.id).first()
    if document_model is None:
        raise HTTPException(status_code=404, detail="Document not found")
    db.query(Document).filter(document_id == Document.id).delete()
    db.commit()


















