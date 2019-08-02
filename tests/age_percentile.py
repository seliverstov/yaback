import requests

from .utils import get_server_api, get_random_citizen


def test_age_percentile():
    server_api = get_server_api()

    citizens = [get_random_citizen(relatives=False) for _ in range(10)]

    citizens[0]['town'] = 'Moscow'
    citizens[1]['town'] = 'Moscow'
    citizens[2]['town'] = 'Moscow'
    citizens[3]['town'] = 'Moscow'
    citizens[4]['town'] = 'Moscow'

    citizens[0]['birth_date'] = '01.01.1990'
    citizens[1]['birth_date'] = '01.02.1980'
    citizens[2]['birth_date'] = '01.03.1980'
    citizens[3]['birth_date'] = '01.04.2000'
    citizens[4]['birth_date'] = '01.05.2010'

    citizens[5]['town'] = 'Saratov'
    citizens[6]['town'] = 'Saratov'
    citizens[7]['town'] = 'Saratov'
    citizens[8]['town'] = 'Saratov'
    citizens[9]['town'] = 'Saratov'

    citizens[5]['birth_date'] = '01.01.2000'
    citizens[6]['birth_date'] = '01.02.2001'
    citizens[7]['birth_date'] = '01.03.2002'
    citizens[8]['birth_date'] = '01.04.2003'
    citizens[9]['birth_date'] = '01.05.2010'

    data = {
        'citizens': citizens
    }
    r = requests.post(f"{server_api}/imports", json=data)
    result = r.json()

    assert r.status_code == 201
    assert "data" in result
    assert "import_id" in result['data']

    import_id = result['data']['import_id']

    r = requests.get(f"{server_api}/imports/{import_id}/towns/stat/percentile/age")
    result = r.json()
    print(f"RESPONSE: {result}")
    assert r.status_code == 200

    p = result['data']

    assert len(p) == 2

    assert p[0]["town"] == "Moscow"
    assert p[0]["p50"] == 29
    assert p[0]["p75"] == 39
    assert p[0]["p99"] == 39

    assert p[1]["town"] == "Saratov"
    assert p[1]["p50"] == 17
    assert p[1]["p75"] == 18
    assert p[1]["p99"] == 18

    r = requests.get(f"{server_api}/imports/10000/towns/stat/percentile/age")
    result = r.json()
    print(f"RESPONSE: {result}")
    assert r.status_code == 404




