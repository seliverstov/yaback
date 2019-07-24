from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from starlette.responses import RedirectResponse, Response
from pymongo import MongoClient
from pymongo.collection import ReturnDocument
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv
from examples import CITIZEN, BIRTHDAYS, STATS

load_dotenv(verbose=True)

MONGO_URL = os.getenv('YB_MONGO_URL')

client = MongoClient(MONGO_URL)

db = client['yaback']

imports = db['imports']


class Citizen(BaseModel):
    citizen_id: int = None
    town: str = None
    street: str = None
    building: str = None
    appartement: int = None
    name: str = None
    birth_date: str = None
    gender: str = None
    relatives: List[int] = None


class Import(BaseModel):
    citizens: List[Citizen]


app = FastAPI()


@app.get("/")
def get_root():
    response = RedirectResponse(url='/docs')
    return response


@app.post("/imports", status_code=201)
def post_imports(data: Import):
    id = imports.insert_one(data.dict()).inserted_id
    return {"data": {"import_id": str(id)}}


@app.patch("/imports/{import_id}/citizens/{citizen_id}")
def patch_citizen(import_id: str, citizen_id: int, data: Citizen, response: Response):
    fields = {k: v for k, v in data.dict().items() if v is not None}
    result = imports.find_one_and_update(
        filter={"_id": ObjectId(import_id), "citizens.citizen_id": citizen_id},
        projection={"citizens.$": True, "_id": False},
        update={"$set": {f"citizens.$.{k}": v for k, v in fields.items()}},
        return_document=ReturnDocument.BEFORE)
    if result is not None:
        citizen = result['citizens'][0]
        citizen.update(fields)
        return {"data": citizen}
    else:
        response.status_code = 400
        return response


@app.get("/imports/{import_id}/citizens")
def get_citizens(import_id: str):
    imp = imports.find_one({"_id": ObjectId(import_id)})
    return {"data": imp['citizens']}


@app.get('/imports/{import_id}/citizens/birthdays')
def get_birthdays(import_id: int):
    print(import_id)
    return {"data": BIRTHDAYS}


@app.get('/imports/{import_id}/towns/stat/percentile/age')
def get_age_stat(import_id: int):
    print(import_id)
    return {"data": STATS}


