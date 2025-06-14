from fastapi import FastAPI
import models
from database import engine
from routers import auth, documents, admin, users, collections
from services import statistics


app = FastAPI()

models.Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(collections.router)
