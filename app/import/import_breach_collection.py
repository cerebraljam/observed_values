import sqlite3
import csv, sys, os, json
import base64
import re
import time

import unicodedata
root = sys.argv[1] or "empty"

batchlines = 6000
bestrate = 0
bestlines = 0
slowingdown = 0
maxlines = 15000

database = './breach_collection4.sqlite3'
statefile = '{}.done.txt'.format(database)
skippedfile = '{}.skipped.txt'.format(database)

db = sqlite3.connect(database)
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT, domain TEXT, password TEXT)')
db.commit()
cursor.execute('CREATE INDEX IF NOT EXISTS idx ON users (email)')
db.commit()
#cursor.execute('CREATE INDEX IF NOT EXISTS dom ON users (domain)')
#db.commit()

db.execute('PRAGMA journal_mode = MEMORY')
db.execute('PRAGMA synchronous = OFF')

db_sessions = [db]

starttime = time.time()

ignored = 0.
totallines = 0.

def extractcreds(line):
	creds = []
	global ignored
	global totallines
	match = False

	line = re.sub('[/]', '', line)
	line = re.sub('\\r\\n', '', line)
	line = re.sub('\\n', '', line)
	totallines+=1

	idx = line.find(':')
	if idx == -1:
		idx = line.find(';')
	if idx == -1:
		idx = line.find('\t')
	if idx == -1:
		idx = line.find('|')
	if idx == -1:
		idx = line.find('  ')

	if idx != -1:
		match = re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", line[:idx])
		email = line[:idx]
		password = line[idx+1:]
		if match:
			creds = [email, password]
	else:
		try:
			line.decode('utf-8')
			utf8 = True
		except UnicodeError:
			utf8 = False
		try:
			line.decode('hex')
			hexbug = False
		except:
			hexbug = True

		if re.match(r'^\\xc3', str(line)):
			ignored = ignored + 1
		elif re.match(r'^$', line):
			ignored = ignored + 1
		elif re.match(r'^$', line):
			ignored = ignored + 1
		elif re.match(r'^\w+$', line):
			ignored = ignored + 1
		elif re.match(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]*)\s*$', line):
			ignored = ignored + 1
		elif re.match(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\?)\s*$', line):
			ignored = ignored + 1
		elif re.match(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]*$)', line):
			ignored = ignored + 1
		elif re.match(r'(^[a-zA-Z0-9_.+-]+$)', line):
			ignored = ignored + 1
		elif utf8 or hexbug:
			ignored = ignored + 1
		else:
			raise Exception('No delimiter found:', line.decode('hex'))

	return creds

def rejecthash(y):
	hashed = False
	if re.match(r'^[a-f0-9]{16,32,40,64,128}:?[a-z0-9]{2}?$', y.lower()):
		hashed = '1 {}'.format(y)
	elif re.match(r'^[a-f0-9]{32,128}$', y.lower()):
		hashed = '1.1 {}'.format(y)
	elif re.match(r'^[a-f0-9]{32}:[a-f0-9]{2}$', y.lower()):
		hashed = '1.2 {}'.format(y)
	elif re.match(r'^B\-[a-f0-9]{160}$', y.lower()):
		hashed = '2 {}'.format(y)
	elif re.match(r'^\$[a-z]{1-2}\$[0-9a-z\/\.]{31,52}$', y.lower()):
		hashed = '3 {}'.format(y)
	elif re.match(r'^\$[a-z0-9]{1-2}\$[a-z0-9]{1-2}\$[0-9a-z\/\.]{53}$', y.lower()):
		hashed = '4 {}'.format(y)
	elif re.match(r'^\$[a-z0-9]{1-2}\$round\=\d+\$[0-9a-z\/\.]{100}$', y.lower()):
		hashed = '5 {}'.format(y)
	elif re.match(r'^\*[a-f0-9]{32,40}$', y.lower()):
		hashed = '6 {}'.format(y)
	elif re.match(r'^[a-z0-9\/\+]{24,32,44}$', y.lower()):
		hashed = '7 {}'.format(y)

	if not hashed:
		while re.match(r'(?:[A-Za-z0-9+/]{4}){2,}(?:[A-Za-z0-9+/]{2}[AEIMQUYcgkosw048]=|[A-Za-z0-9+/][AQgw]==)', y):
			try:
				y = base64.b64decode(y)
			except:
				pass

		if re.match(r'^[ -~]+$', y):
			return y
		else:
			return False
	else:
		return False
	

def insertEntries(creds):
	global starttime
	cursor = db.cursor()

	rows = []
	dejavu = {}
	#print('checking for duplicates for {} credentials'.format(len(creds)))
	duplicatetime = time.time()
	keytotal = 0
	sqltotal = 0
	pwtotal = 0
	inserttotal = 0
	keystart = time.time()
	skippedcred = 0
	foundcred = 0
	inserted = []
	for ii in range(len(creds)):
		# Ugly string fixing stuff
		x = creds[ii][0].lower()

		y = rejecthash(creds[ii][1])
		if y:
			#y = base64.b64encode(creds[ii][1])
			if x not in dejavu.keys():
				dejavu[x] = {}
			dejavu[x][y] = 1
		else:
			#if creds[ii][1]:
			#	print('skipping {}'.format(creds[ii]))
			skippedcred+=1	

	if len(dejavu.keys()):
		for email in dejavu.keys():
			for y in dejavu[email]:
				domain = email.split('@')[1]
				rows.append([email, domain, y])
	keytotal+=time.time() - keystart
	rate = 0

	if len(rows):
		lastEmail = ""
		lastExisting = []
		for r in range(len(rows)):
			email = rows[r][0]

			if email != lastEmail:
				sqlstart = time.time()
				lastEmail = email
				lastExisting = []
				check = 'SELECT email, password FROM users WHERE email = "{}"'.format(email)
	
				for ksess in db_sessions:
					kcur = ksess.cursor()
					kcur.execute(check)
					lastExisting = lastExisting + kcur.fetchall()

				sqltotal += time.time() - sqlstart

			found = False
			pwstart = time.time()
			for e in lastExisting:
				if rows[r][2] == str(e[1]):
					foundcred+=1
					found = True
					break
			pwtotal += time.time() - pwstart
			if not found:
				lastExisting.append([email, rows[r][2]])
				inserted.append(rows[r])

		if len(inserted):
			insertstart = time.time()
			sql = 'INSERT INTO users(email,domain,password) VALUES(?,?,?)'
			db.execute("BEGIN TRANSACTION")
                	cursor.executemany(sql, inserted)
			db.commit()
			inserttotal += time.time() - insertstart
		writesize = len(json.dumps(inserted))
		rate = len(rows)*1.0 / ((time.time() - starttime)*1.0)
                print('* {}/{} in {:0.2f}s ({:0.1f}/s) last: {}, size: {}k, key: {:0.2f}s, sql: {:0.2f}s, pw: {:0.2f}s, insert: {:0.2f}s. {} hash, {} dup'.format(len(inserted),len(creds), time.time() - starttime, rate, rows[-1], writesize/1024, keytotal, sqltotal, pwtotal, inserttotal, skippedcred, foundcred))
		starttime = time.time()
	del dejavu
	del rows
	return rate

def readfile(filepath):
	global bestrate
	global bestlines
	global batchlines
	global maxlines
	global slowingdown
	steprate = 100
	rate = 0

	with open(filepath, 'rb') as f:
		lines = []
		for line in f:
			creds = extractcreds(line)
			if len(creds) == 2:
				lines.append(creds)
			if len(lines) % batchlines == 0 and len(lines) != 0:
				lastrate = insertEntries(lines)

				if lastrate > 0:
					if lastrate > bestrate: 
						bestrate = lastrate
						bestlines = batchlines
						slowingdown -= 1

					if lastrate < rate - steprate:
						batchlines = batchlines - 100
						slowingdown += 1

					elif lastrate >= rate + steprate:
						batchlines = batchlines + 100

					rate = lastrate

				if batchlines < steprate:
					batchlines = steprate
				elif batchlines > maxlines:
					batchlines = maxlines

				if slowingdown > 20:
					print('* Reseting rate to the best observed: {} at {} lines'.format(bestrate, bestlines))
					slowingdown = 0
					batchlines = bestlines

				lines=[]
		if len(lines):
			insertEntries(lines)
	return True

lastone = ''
debug = False
passed = True
file_count = 0
files_lists = []
files_completeds = []
files_skippeds = []

if debug == False:
	pf = open(statefile, 'a+')
	files_completeds = pf.read()

	sf = open(skippedfile, 'a+')

	if os.path.isdir(root):
		for path, subdirs, files in os.walk(root):
			for name in files:
				fullpath = os.path.join(path, name)
				if fullpath not in files_completeds:
					files_lists.append(fullpath)

		files = sorted(files_lists)
		print("Files to process: {}".format(len(files)))
		file_lists = []
		
		for name in files:
			if (name == lastone):
				passed = True
			if passed:
				if name[-4:] == '.txt':
					file_count+=1
					print("\n* file {}/{} {}".format(file_count, len(files), name))
					result = readfile(name)
					if result:
						pf.write(name+"\n")
						file_lists.append(name)
					if debug and file_count:
						passed = False
				else:
					sf.write(name+"\n")
					files_skippeds.append(name)
		sf.close()
		pf.close()
					
			
	else:
		print("folder {} does not exists".format(root))
if debug:
	creds = readfile(lastone)

db.close()
print("Total number of files processed: {}".format(len(file_lists)))
print("Total number of files skipped: {}".format(len(files_skippeds)))
#print("Total ignored lines: {}/{} = {}".format(ignored, totallines, ignored/(totallines if totallines > 0 else 1)))
