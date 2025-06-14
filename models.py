from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Float, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String)

    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="owner", cascade="all, delete-orphan")



class Document(Base):
    __tablename__ = "document"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    path = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    owner = relationship("User", back_populates="documents")
    collections = relationship("Collection", secondary="document_collection_link", back_populates="documents")
    word_stats = relationship("WordStat", back_populates="document", cascade="all, delete-orphan")


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    owner = relationship("User", back_populates="collections")
    documents = relationship("Document", secondary="document_collection_link", back_populates="collections")


class DocumentCollectionLink(Base):
    __tablename__ = "document_collection_link"

    document_id = Column(Integer, ForeignKey("document.id"), primary_key=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), primary_key=True)


class WordStat(Base):
    __tablename__ = "word_stats"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, nullable=False)
    tf = Column(Integer, nullable=False)
    idf = Column(Float, nullable=False)
    document_id = Column(Integer, ForeignKey("document.id"), nullable=False)

    document = relationship("Document", back_populates="word_stats")
