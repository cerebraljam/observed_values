from bitarray import bitarray
import hashlib
import numpy as np
import math
import random

import re
import os

knowledge_filename_pepperless = os.environ.get('FILE', 'knowledge.r.raw.32bits')
allowed_access_keys = os.environ.get('KEY', 'noyfb').split(",")

bit_array_pepperless = False
bit_array_size_pepperless = 0

test_array = bitarray(2**8)
test_array_size = len(test_array)
test_array.setall(0)


def load_file(file):
    array = False
    size = 0
    if os.path.exists(file) != False:
        print("Loading existing knowledge file {}".format(file))

        array = bitarray()
        with open(file, 'rb') as f:
            array.fromfile(f)
        size = len(array)
    else:
        print("knowledge file {} still not found... running in test mode only".format(file))

    return array, size

if knowledge_filename_pepperless:
    bit_array_pepperless, bit_array_size_pepperless = load_file(knowledge_filename_pepperless)

def process_word(word, size):
    x = word.encode('utf-8')
    m = hashlib.md5(x).digest()
    s = hashlib.sha1(x).digest()
    offset_md5 = int.from_bytes(m, "little") % size
    offset_sha1 = int.from_bytes(s, "little") % size
    return {"word": word, "offsetMD5": offset_md5, "offsetSHA1": offset_sha1}

def record_word(array, offset):
    array[offset]=True

def query(words, accesskey):
    idx = 0
    ## This should be refactorised... handling of multiple knowledge files isn't super good now
    array=False

    if accesskey in allowed_access_keys:
        array = bit_array_pepperless
        size = bit_array_size_pepperless

    if array == False:
        array = test_array
        size = len(test_array)

    results = []
    for word in words:
        valid_sha1 = re.search(r"[a-f0-9]{40}", word)
        valid_md5 = re.search(r"[a-f0-9]{32}", word)

        if array != False and (valid_sha1 or valid_md5):
            result = process_word(word, size)
            # print(result, array[result['offsetMD5']], array[result['offsetSHA1']])
            if array[result['offsetMD5']] and array[result['offsetSHA1']]:
                results.append({"word": word, "result": True})
            else:
                results.append({"word": word, "result": False})
    if len(results) == 0:
        results.append({"word": "invalid", "result": False})
    return results

def addkey(key):
    print("* adding key {}".format(key))
    if key not in allowed_access_keys:
        allowed_access_keys.append(key)
    return {'result': True}

def record(target, values):
    results = []

    if target == 'test':
        array = test_array
        size = len(array)
    else: ## The function to update the real knowledge file isn't implemented. but it would be here
        return results

    for word in values:
        valid_sha1 = re.search(r"[a-f0-9]{40}", word)
        valid_md5 = re.search(r"[a-f0-9]{32}", word)

        if array != False and (valid_sha1 or valid_md5):
            result = process_word(word, size)
            record_word(array, result['offsetMD5'])
            record_word(array, result['offsetSHA1'])
            results.append(result)

    return results
