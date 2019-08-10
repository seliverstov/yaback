## REST Service for Yandex Backend School

### Requirements: Python 3.6, MongoDB, Docker (optional)

### Install & Run

```sh
git clone https://github.com/seliverstov/yaback
cd yaback
python3 -m venv env
source ./env/bin/activate
pip3 install -r requirements.txt
export YB_MONGO_URL=<CONNECTION_URL_TO_YOUR_MONGODB>
uvicorn --host 0.0.0.0 --port 8080 --workers 10 main:app
```

### Run with Docker

```sh
git clone https://github.com/seliverstov/yaback
cd yaback
docker build -t yaback:latest .
docker run --name yaback -p 8080:8080 -e YB_MONGO_URL=<CONNECTION_URL_TO_YOUR_MONGODB> -d yaback:latest
```

### Env. variables

* `YB_MONGO_URL` - connection url to MongoDB (by default `mongodb://localhost:27017/`)
* `YB_APP_URL` - application url for testing when run test with `pytest` (by default `http://0.0.0.0:8080`)


### MongoDB

The application will create `yaback` database with two collections: `imports` and `counter`

### Run Test

#### Attention: the collections `imports` and `counter` will be cleared during tests.

* Specify valid `YB_MONGO_URL`.
* Install and run the application. 
* Specify `YB_APP_URL` env. variable if the application runs on another host. 
* Run `pytest -v` from the application root folder

