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
    * generate oauth2 token from client id/secret
    * generate short url
* user model based on enhancement feature
* send log to BigQuery
* datastudio setup

### enhancement
* group user management

## data model
### BillingPlan
plan_name: String
max_user: Integer

### Team
team_name: String
billing_plan: BillingPlan
billing_status: String
primary_owner: User
sub_domain: String
custom_redirect_rule: JSON

### User
email: Email
user_name: String
team: Team
role: String
updated_at: DateTime
created_at: DateTime

### ShortURL
key_name: domain + short_url id
title: String
original_url: String
domain: String
use_team_redirect_rule: Boolean 
custom_redirect_rule: JSON
created_by: User
team: Team
updated_at: DateTime
created_at: DateTime

### Oauth2Token
key_name: token
created_by: User
expired_at: DateTime
updated_at: DateTime
created_at: DateTime

### ApiCall
pay_load: Text
headers: Text
created_by: User
created_at: DateTime

### Click
headers: Text
user_agent: Text
cookie: Text
created_at: DateTime


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
* /{short_url_id}+
    * show analytics for the link

### API
* /api/access_token: return access token
* /api/v1/shorten
    * GET: return recent list
    * POST: create short url
    * PATCH: change short url
    * DELETE: delete
