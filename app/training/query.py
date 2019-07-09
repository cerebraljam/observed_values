from bitarray import bitarray
import hashlib
import base64
import numpy as np
import math
import pickle
import os.path
import sys
import jaconv
from email.utils import parseaddr
import time
import random
import sqlite3

bitsize = 32
bit_array_size = 2**bitsize
bit_array = False
knowledge_filename = "knowledge.r.{}bits".format(bitsize)
count = 0

#testusersdb = '../checkusers/2017breach.search_results.sqlite3'
testusersdb = '../checkusers/collection1.search_results.sqlite3'
pepper = ''

def process_word(word):
    x = word.encode('utf-8')
    m = hashlib.md5(x).digest()
    s = hashlib.sha1(x).digest()
    offset_md5 = int.from_bytes(m, "little") % bit_array_size
    offset_sha1 = int.from_bytes(s, "little") % bit_array_size
    return {"word": word, "offsetMD5": offset_md5, "offsetSHA1": offset_sha1}

def query(bit_array, words):
    founds = []
    notfounds = []
    for word in words:
        result = process_word(word)
        # print(result, bit_array[result['offsetMD5']], bit_array[result['offsetSHA1']])
        if bit_array[result['offsetMD5']] and bit_array[result['offsetSHA1']]:
            founds.append(result)
        else:
            notfounds.append(result)
    return {"founds": founds, "notfounds": notfounds}

def transform_data_format(data, pepper):
    email = data[0].encode('utf-8')
    password = base64.b64decode(data[1]).strip()

    s = hashlib.sha1(pepper.encode('utf-8') + password).hexdigest().encode('utf-8')
    return hashlib.sha1(email + s).hexdigest()


def load_from_sqlite3(bcursor, bit_array):
    global pepper
    samples = {"words": [], "classifs": []}
    sql = 'SELECT email, password FROM users'

    bcursor.execute(sql)
    existings = bcursor.fetchall()

    if len(existings):
        transforms = []
        for e in existings:
            transforms.append(transform_data_format(e, pepper))

        samples = query(bit_array, transforms)

    return samples

if os.path.exists(testusersdb):
    testdb = sqlite3.connect(testusersdb)
    cursor = testdb.cursor()
else:
    print("testdb {} file not found".format(testusersdb))
    sys.exit(0)

if os.path.exists(knowledge_filename) == False:
    print("knowledge file not found")
else:
    print("Loading existing knowledge file")
    start = time.time()
    bit_array = pickle.load( open(knowledge_filename, "rb" ) )
    print("load completed: {}s".format(time.time() - start))

start = time.time()
print("loading and searching all values in the test database")
results = load_from_sqlite3(cursor, bit_array)
print("done: {}s".format(time.time() - start))

testdb.close()
print("Found:", len([x['word'] for x in results['founds']]))
print("Not found:", len([x['word'] for x in results['notfounds']]))
