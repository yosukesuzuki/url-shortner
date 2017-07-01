# URL Shortne application

## initial setup
Setup Google Cloud SDK

[see instruction in google site](https://cloud.google.com/sdk/downloads)

For develeopment
```bash
pip install -t lib -r requirements.txt
```

For test env

```bash
pip install pytest
pip install pyyaml
```

Set python path for local test

```bash
PYTHONPATH="/path/to/google-cloud-sdk/platform/google_appengine:$PYTHONPATH"
export PYTHONPATH
```

run test

```bash
py.test .

```

## endpoint

### GUI

* / : top
    * login user
        * show recent short url
    * not login user
        * show price plan
* /settings : settings
    * domain setting
    * sub user management
    * deep link setting

### API
* /api/access_token: return access token
* /api/v1/shorten
    * GET: return recent list
    * POST: create short url
    * PATCH: change short url
    * DELETE: delete
