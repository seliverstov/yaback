import requests

from .utils import get_server_api, get_random_citizen, clear_mongo_db


def setup():
    clear_mongo_db()


def teardown():
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
    assert r.status_code == 400

    del new_citizen['citizen_id']

    r = requests.patch(f"{server_api}/imports/{import_id}/citizens/{citizen['citizen_id']}", json=new_citizen)
    result = r.json()
    print(f"RESPONSE: {result}")

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
    assert r.status_code == 400

    r = requests.patch(f"{server_api}/imports/10000/citizens/20000", json=new_citizen)
    result = r.json()
    print(f"RESPONSE: {result}")
    assert r.status_code == 400

    new_citizen = get_random_citizen(relatives=True)
    new_citizen['relatives'].append(1_000_000)

    r = requests.patch(f"{server_api}/imports/{import_id}/citizens/{citizen['citizen_id']}", json=new_citizen)
    result = r.json()
    print(f"RESPONSE: {result}")
    assert r.status_code == 400

    new_citizen = get_random_citizen(relatives=False)
    new_citizen['gender'] = 'abc'

    r = requests.patch(f"{server_api}/imports/{import_id}/citizens/{citizen['citizen_id']}", json=new_citizen)
    result = r.json()
    print(f"RESPONSE: {result}")
    assert r.status_code == 400

    for field in ['name', 'town', 'street', 'building']:
        new_citizen = get_random_citizen(relatives=False)
        del new_citizen['citizen_id']
        new_citizen[field] = '1'

        r = requests.patch(f"{server_api}/imports/{import_id}/citizens/{citizen['citizen_id']}", json=new_citizen)
        result = r.json()
        print(f"RESPONSE: {result}")
        assert r.status_code == 200

        new_citizen = get_random_citizen(relatives=False)
        del new_citizen['citizen_id']
        new_citizen[field] = ''

        r = requests.patch(f"{server_api}/imports/{import_id}/citizens/{citizen['citizen_id']}", json=new_citizen)
        result = r.json()
        print(f"RESPONSE: {result}")
        assert r.status_code == 400

        new_citizen = get_random_citizen(relatives=False)
        del new_citizen['citizen_id']
        new_citizen[field] = None

        r = requests.patch(f"{server_api}/imports/{import_id}/citizens/{citizen['citizen_id']}", json=new_citizen)
        result = r.json()
        print(f"RESPONSE: {result}")
        assert r.status_code == 400


def test_patch_with_relatives_update():
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

    import_id = result['data']['import_id']

    citizen = citizens[0]
    citizen_id = citizen['citizen_id']
    del citizen['citizen_id']
    citizen['relatives'].append(2)

    r = requests.patch(f"{server_api}/imports/{import_id}/citizens/{citizen_id}", json=citizen)
    assert r.status_code == 200

    r = requests.get(f"{server_api}/imports/{import_id}/citizens")
    result = r.json()
    print(result)
    cs = result['data']

    for c in cs:
        if c['citizen_id'] == 0:
            assert c['relatives'] == [1, 2]
        if c['citizen_id'] == 2:
            assert c['relatives'] == [3, 4, 0]

    citizen = citizens[2]
    citizen_id = citizen['citizen_id']
    del citizen['citizen_id']
    citizen['relatives'] = [4, 0]

    r = requests.patch(f"{server_api}/imports/{import_id}/citizens/{citizen_id}", json=citizen)
    assert r.status_code == 200

    r = requests.get(f"{server_api}/imports/{import_id}/citizens")
    result = r.json()
    cs = result['data']

    for c in cs:
        if c['citizen_id'] == 3:
            assert c['relatives'] == [4]
        if c['citizen_id'] == 2:
            assert c['relatives'] == [4, 0]

    citizen_id = 4
    r = requests.patch(f"{server_api}/imports/{import_id}/citizens/{citizen_id}", json={"relatives": []})
    assert r.status_code == 200

    r = requests.get(f"{server_api}/imports/{import_id}/citizens")
    result = r.json()
    cs = result['data']

    for c in cs:
        if c['citizen_id'] == 3:
            assert c['relatives'] == []
        if c['citizen_id'] == 2:
            assert c['relatives'] == [0]
        if c['citizen_id'] == 4:
            assert c['relatives'] == []


