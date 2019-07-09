import sqlite3
import csv, sys, os
import base64
import re

import unicodedata
def remove_control_characters(s):
    	#return "".join(ch for ch in s if unicodedata.category(ch)[0]!="C")
        print(s)
	return ''.join(c for c in s if ord(c) >= 32 and ord(c) < 128)

root = './BreachCompilation/data/'

database = 'breach.2017.sqlite3'
db = sqlite3.connect(database)
ignored = 0.
totallines = 0.

def extractcreds(line):
	creds = []
	global ignored
	global totallines
	match = False

	line = re.sub('[/]', '', line)
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


def readfile(filepath):
	with open(filepath, 'rb') as f:
		reader = csv.reader(f)
		lines = []
		try:
			for row in reader:
				issues = []
				row = row[0]
				creds = extractcreds(row)

				if len(creds) ==  2:
					lines.append(creds)
		except csv.Error as e:
			pass
			#sys.exit('file %s, line %d: %s' % (filepath, reader.line_num, e))
	return lines

def insertEntries(creds):

        cursor = db.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT, password TEXT)')
        db.commit()
        cursor.execute('CREATE INDEX IF NOT EXISTS idx ON users (email)')
        db.commit()

	queries = 0 
	lastmail = "" 
	lastpass = ""
	for ii in range(len(creds)):

		# Ugly string fixing stuff
		creds[ii][0] = creds[ii][0].lower()
		creds[ii][1] = base64.b64encode(creds[ii][1])

		if debug:
			print(ii, creds[ii])

		if creds[ii][0] == lastmail and creds[ii][1] == lastpass:
			# skipping
			lastmail = creds[ii][0]
			lastpass = creds[ii][1]
		else:
			sql = 'INSERT INTO users(email,password) VALUES("%s","%s")' % (creds[ii][0], creds[ii][1])
			queries = queries + 1
			cursor.execute(sql)

			lastmail = creds[ii][0]
			lastpass = creds[ii][1]

			if queries % 1000 == 0:
				queries = 0 
				db.commit()
	
	db.commit()

lastone = '../node/BreachCompilation/data/m/a/s'
debug = False 
passed = True
counter = 0
file_count = 0
files_lists = []

if debug == False:
	for path, subdirs, files in os.walk(root):
		for name in files:
			files_lists.append(os.path.join(path, name))

	files = sorted(files_lists)

	for name in files:
		if (name == lastone):
			passed = True
		if passed:
			file_count+=1
			print("file {} {}".format(file_count, name))
			creds = readfile(name)
       			counter = counter + len(creds)
			insertEntries(creds)
			if debug and file_count:
				passed = False

if debug:
	creds = readfile(lastone)
	insertEntries(creds)

db.close()
print("Total number of files: {}/1981 = {}".format(file_count, file_count/1981))
print("Total ignored lines: {}/{} = {}".format(ignored, totallines, ignored/totallines))
