from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
import nfc
import json
from datetime import datetime
from sqlmodel import SQLModel, Field, create_engine

class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    lastscan: int
    

engine = create_engine("postgresql+asyncpg://user:password@localhost/dbname")
app = FastAPI()
def get_nfc_reader():
    clf = nfc.ContactlessFrontend('usb')  # Open connection once
    try:
        yield clf
    finally:
        clf.close()  # Ensure proper cleanup when app shuts down

@app.get("/")
async def index():
    return "I'm sorry, but your API is in another castle!"
@app.get("/read_nfc")
def read_nfc(clf: nfc.ContactlessFrontend = Depends(get_nfc_reader)):
    tag = clf.connect(rdwr={'on-connect': lambda tag: False})
    return {"tag_id": str(tag.identifier)}