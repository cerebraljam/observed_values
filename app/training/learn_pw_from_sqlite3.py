import os.path, os
import sys
import jaconv
import time
import random

from bitarray import bitarray
import hashlib
import numpy as np
import math

import sqlite3
from partitions_filter_config import config_partitions

## config

random.seed(42)

nb_hashes = 4
testing_mode = False
testing_limit = 1000000
record_chance = 0.90
keep_chance = 0.01

breachdbs = ['/media/storage/imported/pwndb.sqlite3']
batch_size = 500000

# Configure the filters in this config file. This should be adjusted according to the number of
# passwords expected per filter
partitions = config_partitions()

## This is how we need to encode the word to be registered
## This function will be called twice, once with the pepper, one without
def transform_data_format(word, pepper):
    word = word.strip().encode('utf-8')
    return hashlib.sha1(pepper.encode('utf-8') + word).hexdigest().encode('utf-8')


# the code starts here

knowledge_filenames = []

for p in partitions:
    knowledge_filenames.append("knowledge.a135X_0710.pwned.{}.{}bits".format(p['label'],p['bitsize']))

bit_arrays = [False for x in range(len(knowledge_filenames))]


count = 0

pepper = os.environ.get('PEPPER', "")
if pepper == "":
    print("export PEPPER='fill me!'")
    sys.exit(0)

if testing_mode:
    print("Starting in testing mode. this can be disabled by setting `testing_mode` to False")

def process_word(word, size, hashes=4):
    offsets = []
    for h in range(hashes):
        payload = str(h).encode('utf-8') + word
        offsets.append(int.from_bytes(hashlib.md5(payload).digest(), "little") % size)

    return {"word": word, "offsets": offsets}

def record_word(filter, offset):
    filter[offset]=True

def learn_stuff(lines, filters, record_chance, keep_chance):
    # print("learning about {} lines".format(len(lines)))
    global count
    global nb_hashes
    global partitions
    global bit_arrays

    start = time.time()
    words = []
    classifs = []
    filtersamples = []

    records = 0

    for ii in range(len(lines)):
        word = lines[ii]
        filter = filters[ii]
        size = 2**partitions[filter]['bitsize']

        p = process_word(word, size, nb_hashes)

        count = count + 1

        if testing_mode:
            record = False
            if random.random() < record_chance:
                record = True
                records+=1
                for o in p['offsets']:
                    record_word(bit_arrays[filter], o)

            if random.random() < keep_chance:
                words.append(word)
                classifs.append(record)
                filtersamples.append(filter)
        else:
            records+=1
            record = True
            for o in p['offsets']:
                record_word(bit_arrays[filter], o)

            if random.random() < keep_chance:
                words.append(word)
                classifs.append(record)
                filtersamples.append(filters[ii])

    end = time.time()
    print("Learned about {}M words in {:0.2f}s. {:0.2f}/s, total {:0.2f}G".format(records/1000000, end-start, records/(end-start), count/1000000000))
    return {"words":words, "classifs": classifs, "filters": filtersamples}

def test_accuracy(samples):
    global nb_hashes
    global partitions
    global bit_arrays

    print("Testing accuracy. Sample size of {}".format(len(samples['words'])))
    successes = []
    misses = []

    for i in range(len(samples['words'])):
        word = samples['words'][i]
        filter = samples['filters'][i]
        size = 2**partitions[filter]['bitsize']
        real = samples['classifs'][i]

        result = process_word(word, size, nb_hashes)

        result['real'] = real
        result['bitsize'] = partitions[filter]['bitsize']
        hit = 0

        for o in result['offsets']:
            if bit_arrays[filter][o] == True:
                hit += 1

        if hit == len(result['offsets']) and real:
            successes.append(result)
        else:
            if hit != len(result['offsets']) and real == False:
                successes.append(result)
            else:
                print("looking for word {} in filter {} size {}. real {}, hit: {}/{}".format(word, filter, size, real, hit, len(result['offsets'])))
                misses.append(result)

    print("success: {}. fail: {}. total searched: {}".format(len(successes), len(misses), len(successes) + len(misses)))
    print("success rate: {}".format(len(successes)/(len(successes) + len(misses))))

    print("Details on the missed:")
    for mi in misses[:10]:
        print(mi)


def getPartition(count):
    for i in range(len(partitions)):

        if partitions[i]['maximum'] > count and count >= partitions[i]['minimum']:
            return i

    print("{} > {} >= {} == No Match".format(partitions[i]['maximum'], count, partitions[i]['minimum']))
    return len(partitions) - 1

def load_from_sqlite3(batch_size, bcursor, record_chance, keep_chance, limit = 0):
    global pepper

    samples = {"words": [], "classifs": [], "filters": []}
    sql = 'SELECT password, frequency FROM words'

    if limit:
        sql = sql + " LIMIT {}".format(limit)

    bcursor.execute(sql)
    existings = bcursor.fetchmany(size=batch_size)

    while (len(existings)):
        transforms = []
        filters = []

        for e in existings:
            filter = getPartition(e[1])

            transforms.append(transform_data_format(e[0], pepper))
            transforms.append(transform_data_format(e[0], ''))

            filters.append(filter)
            filters.append(filter)

        short_samples = learn_stuff(transforms, filters, record_chance, keep_chance)

        samples["words"] = samples["words"] + short_samples["words"]
        samples["classifs"] = samples["classifs"] + short_samples["classifs"]
        samples["filters"] = samples["filters"] + short_samples["filters"]

        existings = bcursor.fetchmany(size=batch_size)

    print("total count: {}".format(count))

    return samples

def create_array(bits):
    size = 2**bits
    print("Initializing memory ({}MB). good for {} records at best".format(size/8/1024/1024, size/2))
    array = bitarray(size)
    array.setall(0)
    return array

def save_array(arrays):
    print("Saving knowledge files...")
    for a in range(len(arrays)):
        print("{} {}".format(a, knowledge_filenames[a]))
        with open(knowledge_filenames[a], 'wb') as f:
            arrays[a].tofile(f)

for i in range(len(knowledge_filenames)):
    if os.path.exists(knowledge_filenames[i]) == False:
        print("Creating a new knowledge file {} size {}".format(knowledge_filenames[i], partitions[i]['bitsize']))
        bit_arrays[i] = create_array(partitions[i]['bitsize'])
        print("size of filter {}: {}".format(i, len(bit_arrays[i])))
    else:
        print("Loading existing knowledge file {}".format(knowledge_filenames[i]))

        bit_arrays[i] = bitarray()
        with open(knowledge_filenames[i], 'rb') as f:
            bit_arrays[i].fromfile(f)

for breachdb in breachdbs:
    if os.path.exists(breachdb):
        print('Loading breach file {}'.format(breachdb))
        bdb = sqlite3.connect(breachdb)
        bcursor = bdb.cursor()
    else:
        print("breachdb {} file not found".format(breachdb))
        sys.exit(0)

    samples = load_from_sqlite3(batch_size, bcursor, record_chance, keep_chance, testing_limit if testing_mode else 0)

    bdb.close()
    save_array(bit_arrays)

    test_accuracy(samples)
