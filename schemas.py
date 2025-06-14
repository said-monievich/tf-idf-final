from pydantic import BaseModel
from typing import List, Dict



class CollectionStatistics(BaseModel):
    tf: Dict[str, float]
    idf: Dict[str, float]


class DocumentOut(BaseModel):
    id: int
    filename: str

    class Config:
        orm_mode = True


class CollectionCreate(BaseModel):
    name: str

class CollectionDocumentIDs(BaseModel):
    id: int
    document_ids: List[int]

    class Config:
        from_attributes = True

class CollectionFull(BaseModel):
    id: int
    name: str
    document_ids: List[int]

    class Config:
        from_attributes = True
