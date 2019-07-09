import hashlib
import math
import json
import os
import time
import sys

import requests

LOCAL=False
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

tstart = time.time()

#### training
HOST = os.environ.get('PUBLIC_URL', 'http://HOSTNAME:8080')
KEY='anonymous'

API_ENDPOINT_RECORD = "{}/v1/record".format(HOST)
API_ENDPOINT_KEY = "{}/v1/addkey".format(HOST)
API_ENDPOINT_NOTPEPPERED = "{}/v1/query?key={}".format(HOST,KEY)

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

print("Total runtime: {:0.4f}s".format(time.time()-tstart))
