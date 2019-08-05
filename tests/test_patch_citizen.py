import requests

from .utils import get_server_api, get_random_citizen, clear_mongo_db


def setup():
    clear_mongo_db()


def test_patch():
    server_api = get_server_api()

    citizen = get_random_citizen(relatives=False)

    data = {
        'citizens': [citizen]
    }
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()

    assert r.status_code == 201
    assert "data" in result
    assert "import_id" in result['data']

    import_id = result['data']['import_id']

    new_citizen = get_random_citizen(relatives=False)

    r = requests.patch(f"{server_api}/imports/{import_id}/citizens/{citizen['citizen_id']}", json=new_citizen)
    result = r.json()
    print(f"RESPONSE: {result}")
    assert r.status_code == 200

    for k, v in result['data'].items():
        if k == "citizen_id":
            assert citizen['citizen_id'] == v
        else:
            assert new_citizen[k] == v

    r = requests.get(f"{server_api}/imports/{import_id}/citizens")
    result = r.json()
    print(f"RESPONSE: {result}")
    citizens = r.json()['data']
    citizen_was_found = False
    for c in citizens:
        if c['citizen_id'] == citizen['citizen_id']:
            citizen_was_found = True
            for k, v in c.items():
                if k != 'citizen_id':
                    assert new_citizen[k] == v

    assert citizen_was_found

    r = requests.patch(f"{server_api}/imports/{import_id}/citizens/{citizen['citizen_id']}", json={})
    result = r.json()
    print(f"RESPONSE: {result}")
    assert r.status_code == 422

    r = requests.patch(f"{server_api}/imports/10000/citizens/20000", json=new_citizen)
    result = r.json()
    print(f"RESPONSE: {result}")
    assert r.status_code == 404




