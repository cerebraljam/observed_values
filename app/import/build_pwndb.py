import sqlite3
import time
import os, sys

breachdbs = ['/media/storage/imported/breach_compilation2017.sqlite3']

database = './pwndb.sqlite3'

db = sqlite3.connect(database)
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS words(id INTEGER PRIMARY KEY, password TEXT, frequency INTEGER)')
db.commit()
cursor.execute('CREATE INDEX IF NOT EXISTS idx ON words (password)')
db.commit()

db.execute('PRAGMA journal_mode = MEMORY')
db.execute('PRAGMA synchronous = OFF')

def update_wordlist(words, loop):
    starttime = time.time()
    for key in words.keys():
        cursor.execute('SELECT password, frequency FROM words WHERE password = ?', [key])
        existings = cursor.fetchall()

        if len(existings) > 0:
            for e in existings:
                words[e[0]] += e[1]
                cursor.execute('UPDATE words SET frequency = ? WHERE password = ?', [words[key], key])
        else:
            cursor.execute('INSERT INTO words(password,frequency) VALUES(?,?)', (key,words[key]))

    db.commit()
    print('{} updated {} entries in {:0.2f}s'.format(loop, len(words.keys()), time.time() - starttime))
    return True


def load_from_sqlite3(size, bcursor):
    sql = 'SELECT password FROM users'
    count = 0
    loop = 0
    starttime = time.time()

    bcursor.execute(sql)
    existings = bcursor.fetchmany(size=size)

    while (len(existings)):
        dejavu = {}
        for e in existings:
            if e[0] not in dejavu.keys():
                dejavu[e[0]] = 1
            else:
                dejavu[e[0]] += 1

        count += len(dejavu.keys())
        loop+=1
        update_wordlist(dejavu, loop)

        existings = bcursor.fetchmany(size=size)

    print("total count: {:0.2f}M in {}s".format(count/1000000, time.time() - starttime))
    return True

for breachdb in breachdbs:
    if os.path.exists(breachdb):
        bdb = sqlite3.connect(breachdb)
        bcursor = bdb.cursor()
    else:
        print("breachdb {} file not found".format(breachdb))
        sys.exit(0)

    load_from_sqlite3(1000000, bcursor)

    bdb.close()

