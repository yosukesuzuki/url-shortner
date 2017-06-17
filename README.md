# App Engine Standard Flask application

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

Libray/Components/OSS

* [reveal.js](https://github.com/hakimel/reveal.js)