import datetime
import os
from collections import defaultdict, Counter
from typing import List

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
from pymongo import MongoClient
from pymongo.collection import ReturnDocument
from starlette.responses import RedirectResponse

load_dotenv(verbose=True)

MONGO_URL = os.getenv('YB_MONGO_URL')

client = MongoClient(MONGO_URL)

db = client['yaback']

imports = db['imports']

counter = db['counter']


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
        datetime.datetime.strptime(v, '%d.%m.%Y')
        return v


class Patch(BaseModel):
    town: str = None
    street: str = None
    building: str = None
    appartement: int = None
    name: str = None
    birth_date: str = None
    gender: str = None
    relatives: List[int] = None

    @validator('birth_date')
    def birth_date_format(cls, v):
        if v is not None:
            datetime.datetime.strptime(v, '%d.%m.%Y')
        return v


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
    c = counter.find_one_and_update(filter={"_id": "import_id"},
                                    update={"$inc": {"c": 1}},
                                    upsert=True,
                                    return_document=ReturnDocument.AFTER)
    import_id = c['c']
    imp['import_id'] = import_id
    id = imports.insert_one(imp).inserted_id
    return {"data": {"import_id": import_id}}


@app.patch("/imports/{import_id}/citizens/{citizen_id}")
def patch_citizen(import_id: int, citizen_id: int, data: Patch):
    fields = {k: v for k, v in data.dict().items() if v is not None}

    if fields == {}:
        raise HTTPException(status_code=422, detail="Empty patch not allowed")

    citizen = imports.find_one_and_update(
        filter={"import_id": import_id, "citizens.citizen_id": citizen_id},
        projection={"citizens.$": True},
        update={"$set": {f"citizens.$.{k}": v for k, v in fields.items()}},
        return_document=ReturnDocument.BEFORE)
    if citizen is not None:
        citizen = citizen['citizens'][0]

        if 'relatives' in fields.keys():

            add_rels = set(fields['relatives']).difference(set(citizen['relatives']))
            del_rels = set(citizen['relatives']).difference(set(fields['relatives']))

            if len(add_rels) > 0:
                imports.update(
                    {"import_id": import_id, "citizens.citizen_id": {"$in": list(add_rels)}},
                    {"push": {f"citizens.$.relatives": citizen_id}}
                )

            if len(del_rels) > 0:
                imports.update(
                    {"import_id": import_id, "citizens.citizen_id": {"$in": list(del_rels)}},
                    {"$pull": {f"citizens.$.relatives": citizen_id}}
                )

        citizen.update(fields)
        return {"data": citizen}
    else:
        raise HTTPException(status_code=404, detail=f"Citizen {citizen_id} in import {import_id} not found")


@app.get("/imports/{import_id}/citizens")
def get_citizens(import_id: int):
    imp = imports.find_one({"import_id": import_id})
    if imp is not None:
        return {"data": imp['citizens']}
    else:
        raise HTTPException(status_code=404, detail=f"Import with id {import_id} not found")


@app.get('/imports/{import_id}/citizens/birthdays')
def get_birthdays(import_id: int):
    imp = imports.find_one({"import_id": import_id})
    if imp is None:
        raise HTTPException(status_code=404, detail=f"Import with id {import_id} not found")

    birthdays = defaultdict(Counter)

    for c in imp['citizens']:
        d, m, y = c['birth_date'].split('.')
        for r in c['relatives']:
            cnt = birthdays[int(m)]
            cnt[r] += 1

    result = {}

    for i in range(1, 13):
        if i in birthdays.keys():
            result[str(i)] = [{"citizen_id": k, "presents": v} for k, v in birthdays[i].items()]
        else:
            result[str(i)] = []

    return {"data": result}


@app.get('/imports/{import_id}/towns/stat/percentile/age')
def get_age_stat(import_id: int):
    imp = imports.find_one({"import_id": import_id})
    if imp is None:
        raise HTTPException(status_code=404, detail=f"Import with id {import_id} not found")

    towns = defaultdict(list)

    year_now = datetime.datetime.now().year

    for c in imp['citizens']:
        d, m, year = c['birth_date'].split('.')
        age = int(year_now) - int(year)
        towns[c['town']].append(age)

    result = []

    print(f"TOWNS: {towns}")

    for town, ages in towns.items():
        result.append({
            "town": town,
            "p50": int(np.percentile(ages, 50, interpolation='linear')),
            "p75": int(np.percentile(ages, 75, interpolation='linear')),
            "p99": int(np.percentile(ages, 99, interpolation='linear'))
        })

    return {"data": result}
