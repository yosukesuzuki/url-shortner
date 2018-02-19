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

Run local dev server

```bash

dev_appserver.py . -A your-project-id

```


Set python path for local test

```bash
PYTHONPATH="/path/to/google-cloud-sdk/platform/google_appengine:$PYTHONPATH"
```

run test

```bash
PYTHONPATH="./lib:$PYTHONPATH" py.test .

```

## features
### MVP
* url shorten
* custom short link
* api
    * generate oauth2 token on setting page 
    * generate short url
* user model based on enhancement feature
* send log to BigQuery
* datastudio setup
* group user management

## data model
see [models.py](models.py)


## endpoint
### GUI

* / : top
    * on custom domain
        * redirect to default page
    * login user
        * show recent short url
    * not login user
        * show landing page 
* /settings : settings
    * domain setting
    * sub user management
    * deep link setting
* /{short_url_id}
    * redirect to url

### API
* /api/access_token: return access token
* /api/v1/shorten
    * GET: return recent list
    * POST: create short url
    * PATCH: change short url
    * DELETE: delete
