import requests
from .utils import get_server_api, get_random_citizen


def test_patch():
    server_api = get_server_api()

    citizens = [get_random_citizen(relatives=False) for _ in range(5)]

    data = {
        'citizens': citizens
    }
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()

    assert r.status_code == 201
    assert "data" in result
    assert "import_id" in result['data']

    import_id = result['data']['import_id']

    new_citizen = get_random_citizen(relatives=False)

    r = requests.get(f"{server_api}/imports/{import_id}/citizens")
    result = r.json()
    print(f"RESPONSE: {result}")
    assert r.status_code == 200

    assert len(result['data']) == len(citizens)

    for c1 in result['data']:
        for c2 in citizens:
            if c1['citizen_id'] == c2['citizen_id']:
                assert c1.keys() == c2.keys()
                for k, v in c1.items():
                    assert c2[k] == v

    r = requests.get(f"{server_api}/imports/10000/citizens")
    result = r.json()
    print(f"RESPONSE: {result}")
    assert r.status_code == 404




