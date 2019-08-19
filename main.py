import datetime
import os
from collections import defaultdict, Counter
from enum import Enum
from logging import getLogger
from typing import List

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, validator, Extra, Schema
from pymongo.collection import ReturnDocument
from starlette.responses import JSONResponse

log = getLogger(__name__)

MONGO_URL = os.getenv('YB_MONGO_URL', 'mongodb://localhost:27017/')

log.info(f"MONGO_URL={MONGO_URL}")

client = AsyncIOMotorClient(MONGO_URL)

db = client['yaback']

imports = db['imports']

counter = db['counter']


class Token(BaseModel):
    token: str


class Gender(str, Enum):
    male = 'male'
    female = 'female'


NonNegIntReq = Schema(..., ge=0)
NonNegIntOpt = Schema(None, ge=0)

NonEmpyStrReq = Schema(..., regex=r"\w|\d")
NonEmptyStrOpt = Schema(None, regex=r"\w|\d")


class Citizen(BaseModel):
    citizen_id: int = NonNegIntReq
    town: str = NonEmpyStrReq
    street: str = NonEmpyStrReq
    building: str = NonEmpyStrReq
    apartment: int = NonNegIntReq
    name: str = NonEmpyStrReq
    birth_date: str = NonEmpyStrReq
    gender: Gender
    relatives: List[int]

    class Config:
        extra = Extra.forbid
        min_anystr_length = 1
        max_anystr_length = 256

    @validator('birth_date')
    def birth_date_format(cls, v):
        d = datetime.datetime.strptime(v, '%d.%m.%Y')
        if d > datetime.datetime.utcnow():
            raise ValueError("birth_date should be in past")
        return v


class Patch(BaseModel):
    town: str = NonEmptyStrOpt
    street: str = NonEmptyStrOpt
    building: str = NonEmptyStrOpt
    apartment: int = NonNegIntOpt
    name: str = NonEmptyStrOpt
    birth_date: str = NonEmptyStrOpt
    gender: Gender = NonEmptyStrOpt
    relatives: List[int] = NonEmptyStrOpt

    class Config:
        extra = Extra.forbid
        min_anystr_length = 1
        max_anystr_length = 256

    @validator('birth_date')
    def birth_date_format(cls, v):
        if v is not None:
            d = datetime.datetime.strptime(v, '%d.%m.%Y')
            if d > datetime.datetime.utcnow():
                raise ValueError("birth_date should be in past")
        return v


class Import(BaseModel):
    citizens: List[Citizen]

    class Config:
        extra = Extra.forbid

    @validator("citizens", whole=True)
    def check_unique_citizen_ids(cls, v):
        ids = [item.citizen_id for item in v]

        if len(ids) != len(set(ids)):
            raise ValueError("citizens must have unique id's")

        return v

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


app = FastAPI(docs_url="/")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.post("/imports", status_code=201)
async def post_imports(data: Import):
    imp = data.dict()
    c = await counter.find_one_and_update(filter={"_id": "import_id"},
                                          update={"$inc": {"c": 1}},
                                          upsert=True,
                                          return_document=ReturnDocument.AFTER)
    import_id = c['c']
    imp['import_id'] = import_id
    await imports.insert_one(imp)
    log.info(f"Created import with id: {import_id}")
    return {"data": {"import_id": import_id}}


@app.patch("/imports/{import_id}/citizens/{citizen_id}")
async def patch_citizen(import_id: int, citizen_id: int, data: Patch):
    fields = {k: v for k, v in data.dict().items() if v is not None}

    if fields == {}:
        raise HTTPException(status_code=400, detail="Empty patch not allowed")

    if "relatives" in fields:
        relatives = fields["relatives"]
        if len(relatives) > 0:
            cursor = imports.aggregate(
                [
                    {"$match": {"import_id": import_id}},
                    {"$unwind": "$citizens"},
                    {"$match": {"citizens.citizen_id": {"$in": fields["relatives"]}}},
                    {"$group": {"_id": None, "count": {"$sum": 1}}}
                ]
            )
            cnt = await cursor.to_list(None)
            if len(cnt) != 1 or cnt[0]['count'] != len(relatives):
                raise HTTPException(status_code=400, detail=f"Some relatives does not exists in import {import_id}")

    citizen = await imports.find_one_and_update(
        filter={"import_id": import_id, "citizens.citizen_id": citizen_id},
        projection={"citizens.$": True},
        update={"$set": {f"citizens.$.{k}": v for k, v in fields.items()}},
        return_document=ReturnDocument.BEFORE)

    if citizen is not None:
        citizen = citizen['citizens'][0]

        if 'relatives' in fields.keys():

            add_rels = set(fields['relatives']).difference(set(citizen['relatives']))
            del_rels = set(citizen['relatives']).difference(set(fields['relatives']))

            log.info(f"New relative for citizen {citizen_id}: {add_rels}")
            log.info(f"Relatives to remove for citizen {citizen_id}: {del_rels}")

            if len(add_rels) > 0:
                await imports.update_many(
                    {"import_id": import_id},
                    {"$push": {"citizens.$[elem].relatives": citizen_id}},
                    array_filters=[{"elem.citizen_id": {"$in": list(add_rels)}}]
                )

            if len(del_rels) > 0:
                await imports.update_many(
                    {"import_id": import_id},
                    {"$pull": {"citizens.$[elem].relatives": citizen_id}},
                    array_filters=[{"elem.citizen_id": {"$in": list(del_rels)}}]
                )

        citizen.update(fields)
        return {"data": citizen}
    else:
        raise HTTPException(status_code=400, detail=f"Citizen {citizen_id} in import {import_id} not found")


@app.get("/imports/{import_id}/citizens")
async def get_citizens(import_id: int):
    imp = await imports.find_one({"import_id": import_id})
    if imp is not None:
        return {"data": imp['citizens']}
    else:
        raise HTTPException(status_code=400, detail=f"Import with id {import_id} not found")


@app.get('/imports/{import_id}/citizens/birthdays')
async def get_birthdays(import_id: int):
    imp = await imports.find_one({"import_id": import_id}, projection={
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
async def get_age_stat(import_id: int):
    imp = await imports.find_one({"import_id": import_id}, projection={
        "import_id": True,
        "citizens.birth_date": True,
        "citizens.town": True
    })
    if imp is None:
        raise HTTPException(status_code=400, detail=f"Import with id {import_id} not found")

    towns = defaultdict(list)

    now = datetime.datetime.utcnow()

    for c in imp['citizens']:
        d, m, year = c['birth_date'].split('.')
        age = now.year - int(year) - ((now.month, now.day) < (int(m), int(d)))
        towns[c['town']].append(age)

    result = []

    log.debug(f"TOWNS: {towns}")

    for town, ages in towns.items():
        result.append({
            "town": town,
            "p50": round(np.percentile(ages, 50, interpolation='linear'), 2),
            "p75": round(np.percentile(ages, 75, interpolation='linear'), 2),
            "p99": round(np.percentile(ages, 99, interpolation='linear'), 2)
        })

    return {"data": result}


@app.post('/clear')
async def clear(data: Token):
    if data.dict()['token'] == os.getenv('YB_TOKEN', '52ce8098-d510-4bbc-88b9-e1a733292786'):
        await imports.drop()
        await counter.drop()
        return {"data": "ok"}
    else:
        raise HTTPException(status_code=400)

