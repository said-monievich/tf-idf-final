from typing import Annotated, List
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text
from fastapi import APIRouter, Depends, HTTPException, Path, status
from models import Document, DocumentCollectionLink, User
from database import SessionLocal
from starlette import status
from pydantic import BaseModel, Field
from .auth import get_current_user
from schemas import DocumentOut
from fastapi import UploadFile, File
import os
from collections import Counter
import math
from fastapi.security import OAuth2PasswordBearer


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(oauth2_scheme)]
)

UPLOAD_DIR = "uploads"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[User, Depends(get_current_user)]


class DocumentRequest(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=3, max_length=100)
    priority: int = Field(gt=0, lt=6)
    complete: bool


class Statistic(BaseModel):
    word: str
    tf: float
    idf: float



#Загрузить новый документ
# noinspection PyTypeChecker
@router.post("/upload/", status_code=status.HTTP_201_CREATED)
async def upload_document(
    collection_id: int,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication failed")

    contents = await file.read()
    text = contents.decode("utf-8")

    #создать новый документ чтобы получить id
    new_doc = Document(
        filename=file.filename,
        path="",
        owner_id=user.id
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    #созранить файл используя id
    filename = f"{new_doc.id}.txt"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

    #апдейтнуть путь ко документу
    new_doc.path = filepath
    db.commit()

    #связать документ с коллекцией
    db.execute(
        sql_text("INSERT INTO document_collection_link (document_id, collection_id) VALUES (:doc_id, :col_id)"),
        {"doc_id": new_doc.id, "col_id": collection_id}
    )

    #рассчитать тф
    words = [w.lower() for w in text.split()]
    tf_counter = Counter(words)

    #рассчитать идф в коллекции
    collection_docs = db.execute(
        sql_text("SELECT document_id FROM document_collection_link WHERE collection_id = :col_id"),
        {"col_id": collection_id}
    ).fetchall()
    total_docs = len(collection_docs)
    doc_freq = Counter()

    for row in collection_docs:
        doc = db.query(Document).filter(Document.id == row[0]).first()
        if doc and os.path.exists(doc.path):
            with open(doc.path, encoding="utf-8") as f:
                doc_words = set(f.read().lower().split())
                doc_freq.update(doc_words)

    word_stats = []
    for word, tf in tf_counter.items():
        df = doc_freq.get(word, 1)
        idf = math.log((total_docs + 1) / df)
        word_stats.append((word, tf, idf))

    top_50 = sorted(word_stats, key=lambda x: x[2], reverse=True)[:50]
    for word, tf, idf in top_50:
        db.execute(
            sql_text("INSERT INTO word_stats (word, tf, idf, document_id) VALUES (:w, :tf, :idf, :doc_id)"),
            {"w": word, "tf": tf, "idf": idf, "doc_id": new_doc.id}
        )

    db.commit()

    return {"document_id": new_doc.id, "filename": new_doc.filename}



#GET /documents/ — получить список документов (“id”: название), загруженным текущим пользователем;
@router.get("/", response_model=List[DocumentOut], status_code=status.HTTP_200_OK)
def read_all_documents(user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication failed")

    documents = db.query(Document).filter(Document.owner_id == user.id).all()
    return [{"id": doc.id, "filename": doc.filename} for doc in documents]

os.makedirs(UPLOAD_DIR, exist_ok=True)



#GET /documents/<document_id> — получить содержимое документа;
# noinspection PyTypeChecker
@router.get("/documents/{document_id}", status_code=status.HTTP_200_OK)
async def read_document(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),  # Убедись, что get_db импортирован
    document_id: int = Path(gt=0)
):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication failed")

    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .filter(Document.owner_id == user.id)
        .first()
    )

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = os.path.join(UPLOAD_DIR, f"{document.id}.txt")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    return {
        "document_id": document.id,
        "title": document.filename,
        "content": content,
    }


#GET /documents/<document_id>/statistics — получить статистику по данному документу (с учётом коллекции);
@router.get("/documents/{document_id}/statistics", response_model=List[Statistic], status_code=status.HTTP_200_OK)
async def get_statistics(
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # проверить юзера
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_id == user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found!")

    # проверить к какой коллекции относится док
    collection_document = (
        db.query(DocumentCollectionLink)
        .filter(DocumentCollectionLink.document_id == document.id)
        .first()
    )
    if not collection_document:
        raise HTTPException(status_code=404, detail="Document is not in any collection.")

    collection_id = collection_document.collection_id

    # запрос всех доков в коллекции
    doc_ids_in_collection = (
        db.query(DocumentCollectionLink.document_id)
        .filter(DocumentCollectionLink.collection_id == collection_id)
        .all()
    )
    doc_ids = [doc_id for (doc_id,) in doc_ids_in_collection]

    # идф во всей коллекции
    word_doc_freq = Counter()
    total_docs = len(doc_ids)


    for doc_id in doc_ids:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            continue  # Skip if document doesn't exist
        path = os.path.join(UPLOAD_DIR, f"{doc.id}.txt")
        if not os.path.exists(path):
            continue  # Skip if file is missing
        with open(path, "r", encoding="utf-8") as f:
            words = set(f.read().lower().split())
            word_doc_freq.update(words)

    # тф/идф документа
    path = os.path.join(UPLOAD_DIR, f"{document.id}.txt")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Document file not found.")

    with open(path, "r", encoding="utf-8") as f:
        words = f.read().lower().split()
        word_tf = Counter(words)

    stats = []
    for word, tf in word_tf.items():
        df = word_doc_freq[word] if word_doc_freq[word] > 0 else 1
        idf = math.log(total_docs / df)
        stats.append({"word": word, "tf": tf, "idf": idf})

    # сортировка по убыванию + 50 слов
    stats = sorted(stats, key=lambda x: -x["idf"])[:50]
    return [Statistic(**stat) for stat in stats]


#DELETE /documents/<document_id> — удалить документ
# noinspection PyTypeChecker
@router.delete("/document/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    document_id: int = Path(gt=0)
):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication failed")

    document_model = (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_id == user.id)
        .first()
    )

    if document_model is None:
        raise HTTPException(status_code=404, detail="Document not found!")


    file_path = os.path.join(UPLOAD_DIR, f"{document_model.id}.txt")
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(document_model)
    db.commit()