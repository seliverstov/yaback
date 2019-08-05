import multiprocessing as mp
import time

import requests

from .utils import get_server_api, get_random_citizen, clear_mongo_db


def setup():
    clear_mongo_db()


def test_import_without_relatives():
    server_api = get_server_api()
    data = {
        'citizens': [get_random_citizen(relatives=False) for _ in range(5)]
    }
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()
    assert r.status_code == 201
    assert "data" in result
    assert "import_id" in result['data']


def test_import_nonmutual_relatives():
    server_api = get_server_api()
    data = {
        'citizens': [get_random_citizen(relatives=True) for _ in range(5)]
    }
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()
    assert r.status_code == 422


def test_import_mutual_relatives():
    server_api = get_server_api()
    citizens = [get_random_citizen(relatives=False) for _ in range(5)]
    citizens[0]['citizen_id'] = 0
    citizens[0]['relatives'] = [1]
    citizens[1]['citizen_id'] = 1
    citizens[1]['relatives'] = [0]
    citizens[2]['citizen_id'] = 2
    citizens[2]['relatives'] = [3, 4]
    citizens[3]['citizen_id'] = 3
    citizens[3]['relatives'] = [2, 4]
    citizens[4]['citizen_id'] = 4
    citizens[4]['relatives'] = [2, 3]

    data = {
        'citizens': citizens
    }
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()
    assert r.status_code == 201
    assert "data" in result
    assert "import_id" in result['data']


def __test_import_int_field(field):
    server_api = get_server_api()
    citizen = get_random_citizen(relatives=False)
    citizen[field] = None
    data = {
        'citizens': [citizen]
    }
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()

    assert r.status_code == 422

    citizen[field] = "abc"
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()

    assert r.status_code == 422

    citizen[field] = "1"
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()

    assert r.status_code == 201
    assert "data" in result
    assert "import_id" in result['data']


def __test_import_str_field(field):
    server_api = get_server_api()
    citizen = get_random_citizen(relatives=False)
    citizen[field] = None
    data = {
        'citizens': [citizen]
    }
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()

    assert r.status_code == 422

    citizen[field] = "a"
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()

    assert r.status_code == 201
    assert "data" in result
    assert "import_id" in result['data']


def __test_import_date_field(field):
    server_api = get_server_api()
    citizen = get_random_citizen(relatives=False)
    citizen[field] = None
    data = {
        'citizens': [citizen]
    }
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()

    assert r.status_code == 422

    citizen[field] = "abc"
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()

    assert r.status_code == 422

    citizen[field] = "40.14.1000"
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()

    assert r.status_code == 422

    citizen[field] = 100000
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()

    assert r.status_code == 422

    citizen[field] = "10.10.2019"
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()

    assert r.status_code == 201
    assert "data" in result
    assert "import_id" in result['data']


def test_import_citizen_id():
    __test_import_int_field('citizen_id')


def test_import_apartment():
    __test_import_int_field('apartment')


def test_import_town():
    __test_import_str_field('town')


def test_import_street():
    __test_import_str_field('street')


def test_import_name():
    __test_import_str_field('name')


def test_import_gender():
    __test_import_str_field('gender')


def test_import_birth_date():
    __test_import_date_field('birth_date')


def test_import_id():
    server_api = get_server_api()
    data = {
        'citizens': [get_random_citizen(relatives=False) for _ in range(5)]
    }
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()
    assert r.status_code == 201
    assert "data" in result
    assert "import_id" in result['data']

    imp1_id = result['data']['import_id']

    assert isinstance(imp1_id, int)

    data = {
        'citizens': [get_random_citizen(relatives=False) for _ in range(5)]
    }

    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()
    assert r.status_code == 201
    assert "data" in result
    assert "import_id" in result['data']

    imp2_id = result['data']['import_id']

    assert isinstance(imp2_id, int)

    assert imp2_id - imp1_id == 1


def __import_task(n: int):

    server_api = get_server_api()
    data = {
        'citizens': [get_random_citizen(relatives=False) for _ in range(n)]
    }
    start = time.time()
    r = requests.post(f"{server_api}/imports", json=data)
    end  = time.time()
    result = r.json()
    assert r.status_code == 201
    assert "data" in result
    assert "import_id" in result['data']

    imp1_id = result['data']['import_id']

    assert isinstance(imp1_id, int)
    assert end - start < 60


def test_heavy_parraller_import():
    with mp.Pool(processes=10) as pool:
        pool.map(__import_task, [10000]*10)


