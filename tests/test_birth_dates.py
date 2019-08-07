import requests

from .utils import get_server_api, get_random_citizen, clear_mongo_db


def setup():
    clear_mongo_db()


def teardown():
    clear_mongo_db()


def test_birth_dates():
    server_api = get_server_api()

    citizens = [get_random_citizen(relatives=False) for _ in range(5)]
    citizens[0]['citizen_id'] = 1
    citizens[0]['relatives'] = [2]
    citizens[1]['citizen_id'] = 2
    citizens[1]['relatives'] = [1]
    citizens[2]['citizen_id'] = 3
    citizens[2]['relatives'] = [4, 5]
    citizens[3]['citizen_id'] = 4
    citizens[3]['relatives'] = [3, 5]
    citizens[4]['citizen_id'] = 5
    citizens[4]['relatives'] = [3, 4]

    citizens[0]['birth_date'] = '01.01.1990'
    citizens[1]['birth_date'] = '01.02.1980'
    citizens[2]['birth_date'] = '01.03.1980'
    citizens[3]['birth_date'] = '01.04.2000'
    citizens[4]['birth_date'] = '01.05.2010'

    data = {
        'citizens': citizens
    }
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()

    assert r.status_code == 201
    assert "data" in result
    assert "import_id" in result['data']

    import_id = result['data']['import_id']

    r = requests.get(f"{server_api}/imports/{import_id}/citizens/birthdays")
    result = r.json()
    print(f"RESPONSE: {result}")
    assert r.status_code == 200

    birth_dates = result['data']

    b1 = birth_dates["1"]
    assert len(b1) == 1
    assert b1[0]['citizen_id'] == 2
    assert b1[0]['presents'] == 1

    b2 = birth_dates["2"]
    assert len(b2) == 1
    assert b2[0]['citizen_id'] == 1
    assert b2[0]['presents'] == 1

    b3 = birth_dates["3"]
    assert len(b3) == 2
    assert b3[0]['citizen_id'] == 4
    assert b3[0]['presents'] == 1

    assert b3[1]['citizen_id'] == 5
    assert b3[1]['presents'] == 1

    b4 = birth_dates["4"]
    assert len(b4) == 2
    assert b4[0]['citizen_id'] == 3
    assert b4[0]['presents'] == 1

    assert b4[1]['citizen_id'] == 5
    assert b4[1]['presents'] == 1

    b5 = birth_dates["5"]
    assert len(b5) == 2
    assert b5[0]['citizen_id'] == 3
    assert b5[0]['presents'] == 1

    assert b5[1]['citizen_id'] == 4
    assert b5[1]['presents'] == 1

    for i in range(6, 13):
        assert birth_dates[str(i)] == []

    r = requests.get(f"{server_api}/imports/10000/citizens/birthdays")
    result = r.json()
    print(f"RESPONSE: {result}")
    assert r.status_code == 404




