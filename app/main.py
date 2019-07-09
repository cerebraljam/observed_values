# -*- coding: utf-8 -*-

from flask import Flask, request, abort
import os
import json

import memory_interface as mi

test_master_password = "super_secret_password"
MASTER_PASSWORD = os.environ.get('MASTER_RECORD_PASSWORD', test_master_password)

app = Flask(__name__)

@app.route('/v1/query', methods=['POST'])
def query_handler():
    accesskey = request.args.get('key')

    raw_payload = request.get_data(as_text=True) or '(empty payload)'

    results = []
    try:
        payloads = json.loads(raw_payload)
    except:
        if len(raw_payload):
            payloads = [raw_payload]
        else:
            payloads = []

    if len(payloads):
        results = mi.query(payloads[:1000000], accesskey)
    return json.dumps(results)

@app.route('/v1/record', methods=['POST'])
def record_handler():
    payload = request.get_json(force=True, cache=True) or {}
    results = []
    if MASTER_PASSWORD != '':
        if payload['password'] == MASTER_PASSWORD and payload['values']:
            if len(payload['values']) > 0:
                results = mi.record('test', payload['values'])

        # elif payload['key'] == MASTER_PASSWORD and payload['db']:
        #     if len(payload['values']) > 0:
        #         results = mi.record(payload['db'], payload['values'])

    return json.dumps(results)

@app.route('/v1/addkey', methods=['POST'])
def addkey_handler():
    payload = request.get_json(force=True, cache=True) or {}
    results = {'result': False}
    if MASTER_PASSWORD != '':
        if payload['password'] == MASTER_PASSWORD and payload['key']:
            if len(payload['key']) > 0:
                results = mi.addkey(payload['key'])

    return json.dumps(results)

@app.route('/')
def root():
    return 'OK'

@app.route('/readiness_check')
def readiness():
    return 'Oracle Ready'

@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500

if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", '127.0.0.1')
    app.run(host=host, port=port, debug=False)
