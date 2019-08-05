import os
import random
import string
from copy import deepcopy

from dotenv import load_dotenv
from pymongo import MongoClient

from .examples import CITIZEN


def get_random_int():
    return random.randint(1, 100)


def get_random_list_of_ints():
    n = random.randint(1, 10)
    return [random.randint(1, 100) for _ in range(n)]


def get_random_lower_string():
    return "".join(random.choices(string.ascii_lowercase, k=32))


def get_server_api():
    server_name = f"http://0.0.0.0:8000"
    return server_name


def get_random_date_str():
    return f"{random.randint(1,25)}.{random.randint(1,12)}.{random.randint(1900, 2019)}"


def get_random_citizen(relatives=False):
    c = deepcopy(CITIZEN)
    for k, v in c.items():
        if isinstance(v, int):
            c[k] = get_random_int()
        elif isinstance(v, str):
            c[k] = get_random_lower_string()

    c['birth_date'] = get_random_date_str()

    if relatives:
        c['relatives'] = get_random_list_of_ints()
    else:
        c['relatives'] = []
    return c


def clear_mongo_db():
    load_dotenv(verbose=True)

    mongo_url = os.getenv('YB_MONGO_URL')

    client = MongoClient(mongo_url)

    db = client['yaback']

    imports = db['imports']

    counter = db['counter']

    imports.drop()

    counter.drop()

