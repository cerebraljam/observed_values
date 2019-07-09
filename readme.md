
# Among X words, was the value Y already observed?

## Context
Let's talk about password leakages. There are plenty of user lists available on the Internet. [Collection 1 contains 2,692,818,238 rows](https://www.troyhunt.com/the-773-million-record-collection-1-data-reach/). These databases are absolutely huge, and searching through them takes a lot of time, or require an indexed database.

## Question:
Is there a way to take all these emails and passwords, and convert them in a format that can be queried quickly, while still being able to carry it arround easily, and preventing extraction of the original information?

### Success criterias

* The solution doesn't keep the hashed version of the values in an extractable form.
* No "sequencial search" is required. The query must be as instantanious as possible.
* Limited chances of false positives, despite the compact memory representation.

# Conclusion (Spoilers)

In this notebook, I used a array of 26 bits (8MB), generated 4,522,376 random words that would have needed at least 139MB of ram if all MD5 hashes were stored in whole.

I get an accuracy of 99.9986%, which isn't too bad! It was wrong only 21 times over a testing sample of 15,000.

## Method Name: Bloom Filter

When I coded this proof of concept, I had the intuition that the method exised already, I just didn't knew how it was called or how other people implemented it. The known name for this method is a [Bloom Filter](https://en.wikipedia.org/wiki/Bloom_filter) ([JP version](https://ja.wikipedia.org/wiki/%E3%83%96%E3%83%AB%E3%83%BC%E3%83%A0%E3%83%95%E3%82%A3%E3%83%AB%E3%82%BF)). A Bloom Filter is a space-efficient Probabilistic Data Structure conceived by Burton Howard Bloom in 1970, so there is nothing new in there, except maybe the implementation.

## The Theory

A hash is normally represented as a string, but it can also be represented as an integer between 0 and 2*128 (340282366920938463463374607431768211456). 

For example, 'bacon'.encode('utf-8') hashed with MD5 has the following HEX representation 7813258ef8c6b632dde8cc80f6bda62f.

This HEX value, in Integer can also be represented as 63339489985812697881294514380540810104

The hex can be compactly stored as a string of 32 characters, or can also be represented as a single bit in a memory range of 3.8685626227668134e+25TB. 

This single bit representation is useful since unless there are collisions in the hashing algorythm, there will not be collisions in the storage, But its obviously too big to be practicle. 

By using modulo, we can devide that number and keep only the remainder, which could fit in a limited memory size, with the consequence that we increase the chances of collisions with other hashes.

If the memory space is sufficiently big enough to fit few times the number of total hash values we want to store, the number of collisions are likely to be less frequent. 

To furtherly reduce our chances of collisions, we can use two different hashing algorythm and activate 2 bits in memory for every value that we want to store.
* If bit A and B are *True*: We know that the specific hash was observed 
* If bit A != B, or A and B are *False*: We know that the value was not observed.

## Approach

There is no magic here. Hex is used to compactly represent large binary values. "Compactly" is the keyword. What if we used that raw binary value, presented it as an integer, and used that integer as an offset that would identify a single bit in an array of bit, instead of using the compressed version that would require multiple bits for a single value? 

Yes, this would require a long array of bits, an array bits of 32 bits takes 512MB of ram, which is still manageable on any recent computer. This bit size can also be adjusted to a smaller value if we can tolerate some false positives.

To ensure that values are properly spaced across the array of bit, we can use hashing algorithms like md5 (128 bits), sha1 (160 bits) or sha256 (256 bits), which obviously would overflow our 32 bits of memory. 

Taking that full hash value and doing a modulo 2^32 allows us to crop it down to a reasonable size, with a small chance of collision, that would translate by having some values called as observed while they weren't. 

To reduce the chance of collision, we can double the number of bits used per observation, by using two hashing algorithm and activating 2 bits per word. 
    * if both bits resulting of the modulo of the md5 hash and sha1 hash are True, it's most likely because the value was observed
    * if not, one of the two offset are at False
    * ... there is still a risk of collision, but it becomes less likely.

### Training
* Step 1) take whatever string we want to query later on (ex.: email + hashed(password)) and hash it using your favorite hashing algorithm (md5 used here for speed purpose).
* Step 2) Initialize an array of bits of a defined size. Here I am using a x bits array. This nb of bits should be adjusted depending of the number of value to observe, and the tolerated rate of collisions
* Step 3) For each hashed credentials, convert the hash binary value into an offset in the form of an integer with two hashing algorithm: md5 and sha1.
* Step 4) Use these offsets to set to True for those 2 bits in our array of bit. 

### Querying
* Step 1) Create a hashed version of the email + password with the same procedure as used during the training
* Step 2) Calculate the offset from the value of the hash with the md5 and sha1 algorithm
* Step 3) Check the values at these specific offset. If both are true, it's highly likely that the value was observed, if one of the two or both are false, the value was probably not observed. There is a likelihood of collision, but it will depend of the size of the array of bits.

### Extra mile
We can know how many values were observed by summing all the bits and deviding the result by 2 from the array of bit... but this take forever. Probably that sampling it and extrapolating the result would give sufficiently precice results... but I haven't checked that hypothesis.

## Initializing the array of bits, and other libraries


```python
from bitarray import bitarray
import hashlib
import numpy as np
import math
import random

# On how many bits are we going to compress the information
bit_array_size = 2**26

# Initialization of the array of bit
bit_array = bitarray(bit_array_size)
bit_array.setall(0)
```


```python
print("The current array of bits takes {}MB in memory".format(bit_array_size/8/1024/1024))
print("This array of bits could theorically be sufficient for {} observed values".format(bit_array_size/2))
```

    The current array of bits takes 8.0MB in memory
    This array of bits could theorically be sufficient for 33554432.0 observed values


## Creating testing data

This section is only necessary for the demonstration of this notebook. For real, we should use the hash generated from the credentials


```python
import string

def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

```

### Word to offset conversion

The `process_word(word)` function receives a word, converts it in unicode, then hash it with md5 and SHA1.
The hashes are then converted into integers, and moduloed with the size of bit array, giving us two offsets in the range of our array of bit.

The `record_word(offset)` function simply takes a defined offset and set the value to True.


```python
def process_word(word):
    x = word.encode('utf-8')
    m = hashlib.md5(x).digest()
    s = hashlib.sha1(x).digest()
    offset_md5 = int.from_bytes(m, "little") % bit_array_size
    offset_sha1 = int.from_bytes(s, "little") % bit_array_size
    return {"word": word, "offsetMD5": offset_md5, "offsetSHA1": offset_sha1}

def record_word(offset):
    bit_array[offset]=True
```

The functions aboves are sufficient to train the memory.

## Training from a list of words

The `generate_content` function will loop until we have a list of test cases of size `size`, recording the word with probability `record_chance`, and keeping the outcome (was observed/was not observed) with probability `keep_chance`.

The result of the execution is that in the end, we will have `size` test results, which represent 0.3% of all the values learned/not learned.


```python
%%time

size = 15000
record_chance = 0.90
keep_chance = 0.003

def generate_content(size, record_chance, keep_chance): 
    words = []
    classifs = []
    count = 0
    records = 0
    memorysize = 0
    
    while len(words) < size:
        count += 1
        result = process_word(randomString(50))
        # Will this word be recorded?
        record = False
        if random.random() < record_chance:
            record = True
            records+=1
            memorysize+=32
            record_word(result['offsetMD5'])
            record_word(result['offsetSHA1'])
        
        if random.random() < keep_chance:
            words.append(result['word'])
            classifs.append(record)
        
    print("Performed {} loops to obtain a sample space of {} samples, recorded {} words".format(count, len(words), records))
    print("keeping all the md5 hashes values for querying would have used {}MB + overhead + index + taxes".format(math.ceil(memorysize/1024/1024)))
    return {"words":words, "classifs": classifs}

outcome = generate_content(size, record_chance, keep_chance)
```

    Performed 5058477 loops to obtain a sample space of 15000 samples, recorded 4552648 words
    keeping all the md5 hashes values for querying would have used 139MB + overhead + index + taxes
    CPU times: user 3min 14s, sys: 812 ms, total: 3min 15s
    Wall time: 3min 19s


## Testing the model

Using the `outcome` from the `generate_content` function, we can start querying the memory and confirm the accuracy of the predictions.


```python
%%time

## testing
successes = []
misses = []
for i in range(len(outcome['words'])):
    result = process_word(outcome['words'][i])
    result['real'] = outcome['classifs'][i]
    result['predicted_md5'] = bit_array[result['offsetMD5']]
    result['predicted_sha1'] = bit_array[result['offsetSHA1']]
    if bit_array[result['offsetMD5']] == outcome['classifs'][i] and bit_array[result['offsetSHA1']] == outcome['classifs'][i]:
        successes.append(result)
    else:
        if bit_array[result['offsetMD5']] != bit_array[result['offsetSHA1']]:
            successes.append(result)
        else: 
            misses.append(result)

print("success: {}. fail: {}. total searched: {}".format(len(successes), len(misses), len(successes) + len(misses)))
print("success rate: {}".format(len(successes)/(len(successes) + len(misses))))

print("Details on the missed (10 firsts):")
for mi in misses[:10]:
    print(mi)
```

    success: 14982. fail: 18. total searched: 15000
    success rate: 0.9988
    Details on the missed (10 firsts):
    {'word': 'tvzneabqlaafymgpniwkvduoeperrhodxpjvivyavctdfpjevd', 'offsetMD5': 29354984, 'offsetSHA1': 6741290, 'real': False, 'predicted_md5': True, 'predicted_sha1': True}
    {'word': 'dbnclilronrjyfvhqwzidvbpbqiqlelfrqvpwfuolbyixxkuof', 'offsetMD5': 61843024, 'offsetSHA1': 63988993, 'real': False, 'predicted_md5': True, 'predicted_sha1': True}
    {'word': 'onxapnwucumdwuecdgazllhzqabxbbkvwnaztyypimfxpvbghi', 'offsetMD5': 27995456, 'offsetSHA1': 54163426, 'real': False, 'predicted_md5': True, 'predicted_sha1': True}
    {'word': 'jektxwljqknypypywlkrtoammzutrobozcpsukzjmyhvwlippz', 'offsetMD5': 66382501, 'offsetSHA1': 27669578, 'real': False, 'predicted_md5': True, 'predicted_sha1': True}
    {'word': 'nrxzcvteemkbgzlkglfyvjkikaqqskxttamdxooqzmsdfjjlku', 'offsetMD5': 21702634, 'offsetSHA1': 35897770, 'real': False, 'predicted_md5': True, 'predicted_sha1': True}
    {'word': 'miuxiqycouxsxkjysjwupxklnolqijtzvbhallytlfsjirmmjn', 'offsetMD5': 19388657, 'offsetSHA1': 65596809, 'real': False, 'predicted_md5': True, 'predicted_sha1': True}
    {'word': 'xthzhdhshjlrcivdphghpaszzmxmvpaznwtckiyocqwizbzmwf', 'offsetMD5': 35558112, 'offsetSHA1': 51126914, 'real': False, 'predicted_md5': True, 'predicted_sha1': True}
    {'word': 'tobviylicpyahtwhvcggsfbcqdudoggipssckhapobajuttlou', 'offsetMD5': 8663265, 'offsetSHA1': 7814166, 'real': False, 'predicted_md5': True, 'predicted_sha1': True}
    {'word': 'nbuwcjxqskrstprrlocxbozwzpgtpejbtqxhrmmasbmmqighvs', 'offsetMD5': 2458232, 'offsetSHA1': 51920559, 'real': False, 'predicted_md5': True, 'predicted_sha1': True}
    {'word': 'sxtmmeuyumabtxplqqfmmidwaebshjmexdizlvodgfkmakbzgn', 'offsetMD5': 23681023, 'offsetSHA1': 17407972, 'real': False, 'predicted_md5': True, 'predicted_sha1': True}
    CPU times: user 64.5 ms, sys: 13.1 ms, total: 77.6 ms
    Wall time: 77.7 ms


# Conclusion

In this notebook, I used a array of 26 bits (8MB), generated 4,522,376 random words that would have needed at least 139MB of ram if hashes were stored in whole.

With an accuracy rate of 99.9983%, it's not too bad! It was wrong only 25 times over a testing sample of 15,000.


## Success criterias

* The solution doesn't keep the hashed version of the values in an extractable form.
    * We can't reverse each bit to it's original MD5 and SHA1 HEX value because the number of times the original hash value was divided by the memory space available is unknown.
    * If we were to try, in the scenario where we are using 32 bits (512MB), each bit could be any value between 
        - [0 to 79000000000000000000000000000] * 2^32 + current bit position, if it's a MD5, or 
        - [0 to 34000000000000000000000000000000000000] * 2^32 + current bit position, if it's a SHA1.
    * Now, let's say that you manage to find which HASH a single value represents. It's just the hash used to address the value in memory. Depending how it was transmitted, that hash is most likely to be the result of a prior hash... or not. Basically, the complexity to guess the orginal value is almost impossible.

* No "sequencial search" is required. The query must be as instantanious as possible.
    * The only "search" I have to do is calculate two offsets, and read the memory at these specific offsets. No search is required.

* Limited chances of false positives, despite the compact memory representation.
    * There is a possibility of false positives, but it's surprisingly low. Using two hashes greatly improved the resiliance to collisions. Planning sufficient space also helped.
    
## Reversing the filter

Let's say that we would like to infer the values of system
