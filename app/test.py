import hashlib
import math
import json
import os
import time
import sys

import requests

LOCAL=True
TEST=False

cleartests = [
    ["test@test.com", "password", True],
    ["test@gonzo.com", "Alicedevil", True],
    ["test@test.test", "AquaMarine", True],
    ["bogus@web.jp", "gondor70", True],
    ["someone@example.com", "Tnk0Mk16VX", True],
    ["name@example.com", "password", True],
    ["hoge@example.com", "jn610122", True],
    ["example@me.com", "21705", True],
    ["john@example.com", "assa123", True],
    ["acount@example.com", "password", False],
    ["garbage@defgfbabgfssgdfssdh3.com", "w%@#$%ha1te24ve5r", False]
]

def transform_data_format_do_hash(pepper, email, password):
    s = hashlib.sha1(pepper.encode('utf-8') + password.encode('utf-8')).hexdigest()
    final = hashlib.sha1(email.encode('utf-8') + s.encode('utf-8')).hexdigest()
    return final


def checklist(API_ENDPOINT, transformeds, tests):
    total = 0

    r = requests.post(url = API_ENDPOINT, data = json.dumps(transformeds))

    datas = json.loads(r.text)

    for i in range(len(datas)):
        assert datas[i]["result"] == tests[i][2], "{} {}. should be {}".format(transformeds[i], datas[i]['result'], tests[i][2])
    return datas

def checksingle(API_ENDPOINT, hash, test):
    total = 0

    r = requests.post(url = API_ENDPOINT, data = hash)
    datas = json.loads(r.text)

    assert datas[0]["result"] == test[2], "{} {}. should be {}".format(test[0], datas[0], test[2])
    return datas

def post_request(API_ENDPOINT, payload):
    r = requests.post(url = API_ENDPOINT, data = json.dumps(payload))
    return json.loads(r.text)


tstart = time.time()


#### training
if not LOCAL:
    print('Production Mode: Replace me with your values') ### Replace
    HOST = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8080')
    KEY='secret1'

else:
    print('Local Mode')
    port = os.environ.get('PORT', '8080')
    HOST="http://127.0.0.1:{}".format(port)
    KEY='testmode'

API_ENDPOINT_RECORD = "{}/v1/record".format(HOST)
API_ENDPOINT_KEY = "{}/v1/addkey".format(HOST)
API_ENDPOINT_NOTPEPPERED = "{}/v1/query?key={}".format(HOST,KEY)

MASTER_PASSWORD = os.environ.get('MASTER_RECORD_PASSWORD', "super_secret_password")

if not TEST:
    print('Running in Real Mode')
    if 1:
        print('* Adding client key')

        payload = {
            'password': MASTER_PASSWORD,
            'key': KEY
        }

        results = post_request(API_ENDPOINT_KEY, payload)
        assert results['result'] == True
else:
    print('Simulated mode')

    if 1:
        print('TRAINING: Testing against the unpeppered database')
        pepper = ''

        ### Recording
        tests = cleartests

        payload = {
            'password': MASTER_PASSWORD,
            'values': []
        }
        transformeds = []
        for t in tests:
            transformed = transform_data_format_do_hash(pepper, t[0], t[1])
            if t[2]:
                payload['values'].append(transformed)

        results = post_request(API_ENDPOINT_RECORD, payload)
        assert len(results) == len(payload['values'])

    print("TRAINING completed")

### testing
if 1: # Testing against the unpeppered database
    print('TEST 1: Testing against the unpeppered database')
    pepper = ''
    endpoint = API_ENDPOINT_NOTPEPPERED
    tests = cleartests

    # Pre-transformation
    transformeds = []
    for t in tests:
        transformed = transform_data_format_do_hash(pepper, t[0], t[1])
        transformeds.append(transformed)

    start = time.time()
    results = checklist(endpoint, transformeds, tests)

    print("Completed {} tests against {} in {:0.4f}s".format(len(results), endpoint, time.time()-start))


if 1: # Testing with one at the time
    print('TEST 2: Testing with one at the time')
    pepper = ''
    endpoint = API_ENDPOINT_NOTPEPPERED
    tests = cleartests

    # Pre-transformation
    transformeds = []
    for t in tests:
        transformed = transform_data_format_do_hash(pepper, t[0], t[1])
        transformeds.append(transformed)

    start = time.time()
    results = []
    start = time.time()
    for t in range(len(tests)):
        results.append(checksingle(endpoint, transformeds[t], tests[t])[0])
    print("Completed {} tests against {} in {:0.4f}s".format(len(results), endpoint, time.time()-start))


# API_ENDPOINT = "http://127.0.0.1:8080/v1/query"
print("Total runtime: {:0.4f}s".format(time.time()-tstart))
