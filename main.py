import datetime
import os
from collections import defaultdict, Counter
from typing import List
from logging import getLogger
import numpy as np
from enum import Enum
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, validator
from pymongo import MongoClient
from pymongo.collection import ReturnDocument
from starlette.responses import RedirectResponse, PlainTextResponse, JSONResponse

log = getLogger(__name__)

MONGO_URL = os.getenv('YB_MONGO_URL', 'mongodb://localhost:27017/')

log.info(f"MONGO_URL={MONGO_URL}")

client = MongoClient(MONGO_URL)

db = client['yaback']

imports = db['imports']

counter = db['counter']


class Token(BaseModel):
    token: str


class Gender(str, Enum):
    male = 'male'
    female = 'female'


class Citizen(BaseModel):
    citizen_id: int
    town: str
    street: str
    building: str
    apartment: int
    name: str
    birth_date: str
    gender: Gender
    relatives: List[int]

    @validator('birth_date')
    def birth_date_format(cls, v):
        datetime.datetime.strptime(v, '%d.%m.%Y')
        return v


class Patch(BaseModel):
    town: str = None
    street: str = None
    building: str = None
    apartment: int = None
    name: str = None
    birth_date: str = None
    gender: Gender = None
    relatives: List[int] = None

    @validator('birth_date')
    def birth_date_format(cls, v):
        if v is not None:
            datetime.datetime.strptime(v, '%d.%m.%Y')
        return v


class Import(BaseModel):
    citizens: List[Citizen]

    @validator("citizens", whole=True)
    def relatives_must_be_mutual(cls, v):
        citizens = {}

        for item in v:
            citizens[item.citizen_id] = item.relatives

        for c, rs in citizens.items():
            for r in rs:
                if (r not in citizens) or (c not in citizens[r]):
                    log.debug(f"CHECK PAIR {c} {r}")
                    raise ValueError("relatives must be mutual")
        return v


app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


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
    imports.insert_one(imp)
    log.info(f"Created import with id: {import_id}")
    return {"data": {"import_id": import_id}}


@app.patch("/imports/{import_id}/citizens/{citizen_id}")
def patch_citizen(import_id: int, citizen_id: int, data: Patch):
    fields = {k: v for k, v in data.dict().items() if v is not None}

    if fields == {}:
        raise HTTPException(status_code=400, detail="Empty patch not allowed")

    if "relatives" in fields:
        relatives = fields["relatives"]
        if len(relatives) > 0:
            cnt = imports.count(flter={"import_id": import_id, "citizens.citizen_id": {"$in": fields["relatives"]}})
            if cnt != len(relatives):
                raise HTTPException(status_code=400, detail=f"Some relatives does not exists in import {import_id}")

    citizen = imports.find_one_and_update(
        filter={"import_id": import_id, "citizens.citizen_id": citizen_id},
        projection={"citizens.$": True},
        update={"$set": {f"citizens.$.{k}": v for k, v in fields.items()}},
        return_document=ReturnDocument.BEFORE)

    # TODO Check if in relatives present on existing id

    if citizen is not None:
        citizen = citizen['citizens'][0]

        if 'relatives' in fields.keys():

            add_rels = set(fields['relatives']).difference(set(citizen['relatives']))
            del_rels = set(citizen['relatives']).difference(set(fields['relatives']))

            log.info(f"New relative for citizen {citizen_id}: {add_rels}")
            log.info(f"Relatives to remove for citizen {citizen_id}: {del_rels}")

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
        raise HTTPException(status_code=400, detail=f"Citizen {citizen_id} in import {import_id} not found")


@app.get("/imports/{import_id}/citizens")
def get_citizens(import_id: int):
    imp = imports.find_one({"import_id": import_id})
    if imp is not None:
        return {"data": imp['citizens']}
    else:
        raise HTTPException(status_code=400, detail=f"Import with id {import_id} not found")


@app.get('/imports/{import_id}/citizens/birthdays')
def get_birthdays(import_id: int):
    imp = imports.find_one({"import_id": import_id}, projection={
        "import_id": True,
        "citizens.birth_date": True,
        "citizens.relatives": True
    })
    if imp is None:
        raise HTTPException(status_code=400, detail=f"Import with id {import_id} not found")

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
    imp = imports.find_one({"import_id": import_id}, projection={
        "import_id": True,
        "citizens.birth_date": True,
        "citizens.town": True
    })
    if imp is None:
        raise HTTPException(status_code=400, detail=f"Import with id {import_id} not found")

    towns = defaultdict(list)

    year_now = datetime.datetime.now().year

    for c in imp['citizens']:
        d, m, year = c['birth_date'].split('.')
        age = int(year_now) - int(year)
        towns[c['town']].append(age)

    result = []

    log.debug(f"TOWNS: {towns}")

    for town, ages in towns.items():
        result.append({
            "town": town,
            "p50": int(np.percentile(ages, 50, interpolation='linear')),
            "p75": int(np.percentile(ages, 75, interpolation='linear')),
            "p99": int(np.percentile(ages, 99, interpolation='linear'))
        })

    return {"data": result}


@app.post('/clear')
def clear(data: Token):
    if data.dict()['token'] == os.getenv('YB_TOKEN', '52ce8098-d510-4bbc-88b9-e1a733292786'):
        imports.drop()
        counter.drop()
        return {"data": "ok"}
    else:
        raise HTTPException(status_code=400)

