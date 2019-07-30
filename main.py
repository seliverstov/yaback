from fastapi import FastAPI
from pydantic import BaseModel, validator
from typing import List
from starlette.responses import RedirectResponse, Response
from pymongo import MongoClient
from pymongo.collection import ReturnDocument
from bson.objectid import ObjectId
from collections import defaultdict
import os
from dotenv import load_dotenv
import datetime
from tests.examples import CITIZEN, BIRTHDAYS, STATS

load_dotenv(verbose=True)

MONGO_URL = os.getenv('YB_MONGO_URL')

client = MongoClient(MONGO_URL)

db = client['yaback']

imports = db['imports']


class Citizen(BaseModel):
    citizen_id: int
    town: str
    street: str
    building: str
    appartement: int
    name: str
    birth_date: str
    gender: str
    relatives: List[int]

    @validator('birth_date')
    def birth_date_format(cls, v):
        return datetime.datetime.strptime(v, '%d.%m.%Y')


class Patch(BaseModel):
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

    @validator("citizens", whole=True)
    def relatives_must_be_mutual(cls, v, **kwargs):
        citizens = {}

        for item in v:
            citizens[item.citizen_id] = item.relatives

        for c, rs in citizens.items():
            for r in rs:
                if (r not in citizens) or (c not in citizens[r]):
                    print(f"CHECK PAIR {c} {r}")
                    raise ValueError("relatives must be mutual")
        return v


app = FastAPI()


@app.get("/")
def get_root():
    response = RedirectResponse(url='/docs')
    return response


@app.post("/imports", status_code=201)
def post_imports(data: Import):
    imp = data.dict()
    id = imports.insert_one(imp).inserted_id
    return {"data": {"import_id": str(id)}}


@app.patch("/imports/{import_id}/citizens/{citizen_id}")
def patch_citizen(import_id: str, citizen_id: int, data: Patch, response: Response):
    fields = {k: v for k, v in data.dict().items() if v is not None}
    citizen = imports.find_one_and_update(
        filter={"_id": ObjectId(import_id), "citizens.citizen_id": citizen_id},
        projection={"citizens.$": True, "_id": False},
        update={"$set": {f"citizens.$.{k}": v for k, v in fields.items()}},
        return_document=ReturnDocument.BEFORE)
    if citizen is not None:
        citizen = citizen['citizens'][0]

        if 'relatives' in fields.keys():

            add_rels = set(fields['relatives']).difference(set(citizen['relatives']))
            del_rels = set(citizen['relatives']).difference(set(fields['relatives']))

            imports.update(filter={"_id": ObjectId(import_id), "citizens.citizen_id": {"$in": add_rels}},
                           update={"push": {f"citizens.$.relatives": citizen_id}})

            imports.update(filter={"_id": ObjectId(import_id), "citizens.citizen_id": {"$in": del_rels}},
                           update={"$pull": {f"citizens.$.relatives": citizen_id}})

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


