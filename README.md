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
pip install pillow
```

# create files
## credential.json: file of GCP credential

used for BigQuery integration, run `/_admin/createbq` after first deploy

```
{
  "type": "service_account",
  "project_id": "hoge",
  "private_key_id": "xxxxxxxxxx",
  "private_key": "-----BEGIN PRIVATE KEY-----xxxxx\n-----END PRIVATE KEY-----\n",
  "client_email": "xxxxx@xxxxxxxxxxx.iam.gserviceaccount.com",
  "client_id": "xxxxx",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://accounts.google.com/o/oauth2/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/xxxxxx"
}
```

## config.json: file of other settings
```
{
  "sendgrid_api_key": "SG.xxxx",
  "sendgrid_template_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "sendgrid_from_email":"noreply@xxxxxxxxxxxx"
}
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
* TODO: /api/access_token: return access token
* /api/v1/shorten
    * GET: return recent list
    * POST: create short url
    * PATCH: change short url
    * DELETE: delete
