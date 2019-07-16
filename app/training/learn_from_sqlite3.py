import os.path
import sys
import jaconv
import time
import random

from bitarray import bitarray
import hashlib
import numpy as np
import math

import sqlite3

random.seed(42)

# On how many bits are we going to compress the information
bitsize = 34
bit_array_size = 2**bitsize
bit_array = False

knowledge_filename = "knowledge.a1345X7_0710.prod.{}bits".format(bitsize)

breachdbs = ['/media/storage/imported/breach_ap_myr_zabugor2.sqlite3', '/media/storage/imported/breach_collection1.sqlite3', '/media/storage/imported/breach_collection3.sqlite3', '/media/storage/imported/breach_collection4.sqlite3','/media/storage/imported/breach_collection5.sqlite3', '/media/storage/imported/breach_compilation2017.sqlite3', '/media/storage/imported/breach_collectionX_jp.sqlite3']

count = 0
pepper = ''
emailOnly = False

testing_mode = False
testing_limit = 100000

if testing_mode:
    print("Starting in testing mode. this can be disabled by setting `testing_mode` to False")

record_chance = 0.90
keep_chance = 0.001

def create_array(size):
    print("Initializing memory ({}MB). good for {} records at best".format(size/8/1024/1024, size/2))
    bit_array = bitarray(bit_array_size)
    bit_array.setall(0)
    return bit_array

def save_array(bit_array):
    print("Saving knowledge file")

    with open(knowledge_filename, 'wb') as f:
        bit_array.tofile(f)

def process_word(word):
    x = word.encode('utf-8')
    m = hashlib.md5(x).digest()
    s = hashlib.sha1(x).digest()
    offset_md5 = int.from_bytes(m, "little") % bit_array_size
    offset_sha1 = int.from_bytes(s, "little") % bit_array_size
    return {"word": word, "offsetMD5": offset_md5, "offsetSHA1": offset_sha1}

def record_word(offset):
    bit_array[offset]=True


def learn_stuff(lines, record_chance, keep_chance):
    # print("learning about {} lines".format(len(lines)))
    global count
    start = time.time()
    words = []
    classifs = []
    memorysize = 0
    records = 0

    for ii in lines:
        p = process_word(ii)
        count = count + 1

        if testing_mode:
            record = False
            if random.random() < record_chance:
                record = True
                records+=1
                memorysize+=32
                record_word(p['offsetMD5'])
                record_word(p['offsetSHA1'])

            if random.random() < keep_chance:
                words.append(p['word'])
                classifs.append(record)
        else:
            records+=1
            memorysize+=32
            record = True
            record_word(p['offsetMD5'])
            record_word(p['offsetSHA1'])

            if random.random() < keep_chance:
                words.append(p['word'])
                classifs.append(record)

    end = time.time()
    print("Learned about {}M words in {:0.2f}s. {:0.2f}/s, total {:0.2f}G".format(records/1000000, end-start, records/(end-start), count/1000000000))
    # print("Keeping all the MD5 values would take ~{}MB".format(math.ceil(memorysize/1024/1024)))
    return {"words":words, "classifs": classifs}

def test_accuracy(samples):
    print("Testing accuracy. Sample size of {}".format(len(samples['words'])))
    successes = []
    misses = []
    for i in range(len(samples['words'])):
        result = process_word(samples['words'][i])
        result['real'] = samples['classifs'][i]
        result['predicted_md5'] = bit_array[result['offsetMD5']]
        result['predicted_sha1'] = bit_array[result['offsetSHA1']]

        if bit_array[result['offsetMD5']] == samples['classifs'][i] and bit_array[result['offsetSHA1']] == samples['classifs'][i]:
            successes.append(result)
        else:
            if bit_array[result['offsetMD5']] != bit_array[result['offsetSHA1']]:
                successes.append(result)
            else:
                misses.append(result)

    print("success: {}. fail: {}. total searched: {}".format(len(successes), len(misses), len(successes) + len(misses)))
    print("success rate: {}".format(len(successes)/(len(successes) + len(misses))))

    print("Details on the missed:")
    for mi in misses[:len(misses) - 10]:
        print(mi)


#### THIS IS WHERE WE CONFIGURE HOW THE DATABASE WILL TRAINED
def transform_data_format(data, pepper):
    email = data[0].encode('utf-8')
    #password = base64.b64decode(data[1]).strip()
    password = data[1].strip().encode('utf-8')

    if emailOnly:
        if pepper != '':
             e = hashlib.md5(pepper.encode('utf-8') + email).hexdigest().encode('utf-8')
        else:
             print('email only but no salt defined')
             sys.exit(0)

        return hashlib.sha1(e).hexdigest()
    else:
        if pepper != '':
    	    s = hashlib.sha1(pepper.encode('utf-8') + password).hexdigest().encode('utf-8')
        else:
            s = hashlib.sha1(password).hexdigest().encode('utf-8')
        return hashlib.sha1(email + s).hexdigest()

def load_from_sqlite3(size, bcursor, record_chance, keep_chance, limit = 0):
    global pepper
    samples = {"words": [], "classifs": []}
    sql = 'SELECT email, password FROM users'
    if limit:
        sql = sql + " LIMIT {}".format(limit)

    bcursor.execute(sql)
    existings = bcursor.fetchmany(size=size)
    while (len(existings)):
        transforms = []
        for e in existings:
            transforms.append(transform_data_format(e, pepper))

        short_samples = learn_stuff(transforms, record_chance, keep_chance)
        samples["words"] = samples["words"] + short_samples["words"]
        samples["classifs"] = samples["classifs"] + short_samples["classifs"]
        existings = bcursor.fetchmany(size=size)
    print("total count: {}".format(count))
    return samples


for breachdb in breachdbs:
    if os.path.exists(breachdb):
        print('Loading breach file {}'.format(breachdb))
        bdb = sqlite3.connect(breachdb)
        bcursor = bdb.cursor()
    else:
        print("breachdb {} file not found".format(breachdb))
        sys.exit(0)


    if os.path.exists(knowledge_filename) == False:
        print("Creating a new knowledge file")
        bit_array = create_array(bit_array_size)
    else:
        print("Loading existing knowledge file")

        bit_array = bitarray()
        with open(knowledge_filename, 'rb') as f:
            bit_array.fromfile(f)
        size = len(bit_array)

    samples = load_from_sqlite3(1000000, bcursor, record_chance, keep_chance, testing_limit if testing_mode else 0)

    bdb.close()
    save_array(bit_array)
    test_accuracy(samples)
