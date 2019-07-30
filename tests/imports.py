import requests
from .utils import get_server_api, get_random_citizen


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

