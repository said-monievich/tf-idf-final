from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from typing import List
from services.statistics import compute_tf_idf_for_collection
from models import Collection, Document
from schemas import CollectionCreate, CollectionDocumentIDs, CollectionFull
from database import get_db
from routers.auth import get_current_user


router = APIRouter(prefix="/collections", tags=["collections"])

user_dependency = Depends(get_current_user)
db_dependency = Depends(get_db)


#GET /collections/ — получить список коллекций с id и списком входящих в них документов;
@router.get("/", response_model=List[CollectionFull])
async def get_collections(user=user_dependency, db=db_dependency):
    collections = db.query(Collection).filter(Collection.owner_id == user.id).all()
    return [
        CollectionFull(
            id=c.id,
            name=c.name,
            document_ids=[d.id for d in c.documents]
        )
        for c in collections
    ]


#GET /collections/<collection_id> — получить список id документов, входящих в конкретную коллекцию;
@router.get("/{collection_id}", response_model=CollectionDocumentIDs)
async def get_collection_documents(collection_id: int, user=user_dependency, db=db_dependency):
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.owner_id == user.id
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    return {
        "id": collection.id,
        "document_ids": [d.id for d in collection.documents]
    }


#GET /collections/<collection_id>/statistics — получить статистику по коллекции
# noinspection PyTypeChecker
@router.get("/{collection_id}/statistics", status_code=status.HTTP_200_OK)
async def get_collection_statistics(
    collection_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection or collection.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Collection not found or access denied")

    if not collection.documents:
        raise HTTPException(status_code=400, detail="Collection is empty")

    all_documents = db.query(Document).all()
    tf_idf = compute_tf_idf_for_collection(collection.documents, all_documents)
    return {"tf_idf": tf_idf}


#POST /collection/<collection_id>/<document_id> —добавить документ в коллекцию / возможность добавить документ в несколько коллекций;
@router.post("/{collection_id}/{document_id}", status_code=status.HTTP_200_OK)
async def add_document_to_collection(collection_id: int, document_id: int, user=user_dependency, db=db_dependency):
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.owner_id == user.id
    ).first()

    document = db.query(Document).filter(
        Document.id == document_id,
        Document.owner_id == user.id
    ).first()

    if not collection or not document:
        raise HTTPException(status_code=404, detail="Collection or Document not found")

    if document in collection.documents:
        raise HTTPException(status_code=400, detail="Document already in collection")

    collection.documents.append(document)
    db.commit()
    return {"message": "Document added"}


#create collection
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_collection(name: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # Check if the name is already used by this user
    existing = db.query(Collection).filter(Collection.name == name, Collection.owner_id == user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Collection with this name already exists.")

    new_collection = Collection(name=name, owner_id=user.id)
    db.add(new_collection)
    db.commit()
    db.refresh(new_collection)

    return {"collection_id": new_collection.id, "name": new_collection.name}


#DELETE /collection/<collection_id>/<document_id> — удалить документ из коллекции.
@router.delete("/{collection_id}/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document_from_collection(collection_id: int, document_id: int, user=user_dependency, db=db_dependency):
    collection = db.query(Collection).filter(
        Collection.id == collection_id,
        Collection.owner_id == user.id
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    document = next((doc for doc in collection.documents if doc.id == document_id), None)
    if not document:
        raise HTTPException(status_code=404, detail="Document not in collection")

    collection.documents.remove(document)
    db.commit()











