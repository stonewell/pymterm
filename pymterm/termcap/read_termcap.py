import os
import re
import sys

_entry_cache = {}

MAX_DEPTH = 25

def get_entry(termcap_filepath, name):
	return _get_entry(termcap_filepath, name, 0)

def _expand_cap(termcap_filepath, cap, depth):
	parts = ['']
	for p in cap.split(':'):
		if p.startswith('tc='):
			newcap = _get_entry(termcap_filepath, p[len('tc='):], depth + 1)

			if newcap is not None:
				parts.extend([x for x in newcap.split(':') if len(x) > 0])
		elif len(p) > 0:
			parts.append(p)

	parts.append('')
	
	return ':'.join(parts)

def _get_entry(termcap_filepath, name, depth):
	if name in _entry_cache:
		return _expand_cap(termcap_filepath, _entry_cache[name], depth)

	if depth > MAX_DEPTH:
		return None

	f = open(termcap_filepath, 'r')

	lineno = 0

	entry = ''
	for l in f.readlines():
		lineno += 1

		l = l.strip()
		
		#skip empty and comment
		if len(l) == 0 or l[0] == '#':
			continue

		#if line continue
		if l[-1] == '\\':
			entry = ''.join([entry, l[:-1]])
			continue
		else:
			entry = ''.join([entry, l])

		#find names
		parts = re.split(r'(\||:)', entry)

		names = []
		cap = ''
		for i in range(len(parts)):
			p = parts[i]
			if p == ':':
				if i + 1 < len(parts):
					cap = ''.join(parts[i + 1:])
				break
			if p == '|':
				continue
			names.append(p)

		if name in names:
			cap = _expand_cap(termcap_filepath, cap, depth)
		
		#cache name with cap
		for n in names:
			_entry_cache[n] = cap

		if name in names:
			break

		entry = ''

	f.close()
	
	return _entry_cache[name]
		
if __name__ == '__main__':
	print get_entry(sys.argv[1], 'xterm-color'), '\n'		
	print get_entry(sys.argv[1], 'linux'), '\n'		
	print get_entry(sys.argv[1], 'putty'), '\n'		

		
		
	
	
