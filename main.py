from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from starlette.responses import RedirectResponse
from examples import CITIZEN, BIRTHDAYS, STATS


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


class Import(BaseModel):
    citizens: List[Citizen]


app = FastAPI()


@app.get("/")
def get_root():
    response = RedirectResponse(url='/docs')
    return response


@app.post("/imports", status_code=201)
def post_imports(data: Import):
    print(data)
    return {"data": {"import_id": 1}}


@app.patch("/imports/{import_id}/citizens/{citizen_id}")
def patch_citizen(import_id: int, citizen_id: int, data: Citizen):
    print(import_id, citizen_id, data)
    return {"data": data}


@app.get("/imports/{import_id}/citizens")
def get_citizens(import_id: int):
    print(import_id)
    return {"data": [CITIZEN, CITIZEN]}


@app.get('/imports/{import_id}/citizens/birthdays')
def get_birthdays(import_id: int):
    print(import_id)
    return {"data": BIRTHDAYS}


@app.get('/imports/{import_id}/towns/stat/percentile/age')
def get_age_stat(import_id: int):
    print(import_id)
    return {"data": STATS}


