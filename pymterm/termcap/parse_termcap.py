import os
import sys

class Cap:
	def __init__(self):
		self.flags = {}
		self.cmds = {}
		self.data_parse_tree_root = ControlDataParserTreeNode()
		
def parse_cap(cap_str):
	cap = Cap()
	
	for field in cap_str.split(':'):
		if len(field) == 0:
			continue

		if field.find('=') > 0:
			cap.cmds.update(parse_str_cap(field, cap.data_parse_tree_root))
		elif field.find('#') > 0:
			parts = field.split('#')
			cap.flags.update({parts[0]:int(parts[1])})
		else:
			cap.flags.update({field:1})

	return cap

class ControlDataParserTreeNode:
	def __init__(self):
		self.cap_name = ''
		self.next_nodes = {}
		self.increase = False
		self.num_params_count = 0
		self.num_params = []

class CapStringValue:
	def __init__(self):
		self.padding = 0.0
		self.value = ''
		self.name = ''

	def __str__(self):
		return ','.join([self.name, str(self.padding), self.value])

	def __repr__(self):
		return self.__str__()
		
def parse_str_cap(field, root):
	cap_str_value = CapStringValue()
	
	parts = field.split('=')

	cap_str_value.name = parts[0]
	value = cap_str_value.value = '='.join(parts[1:])

	#padding
	pos = 0

	if value[0].isdigit():
		padding_chars = []
		has_dot = False

		for pos in range(len(value)):
			if value[pos] == '*':
				if len(padding_chars) > 0:
					padding_chars.append('*')
					pos += 1
					break
			elif value[pos] == '.':
				if has_dot:
					break
				has_dot = True
				padding_chars.append('.')
			elif value[pos].isdigit():
				padding_chars.append(value[pos])
			else:
				break
		#end for
		
		try:
			padding = 0.0
			if padding_chars[-1] == '*':
				padding = float(''.join(padding_chars[:-1]))
			else:
				padding = float(''.join(padding_chars))

			cap_str_value.padding = padding
		except ValueError:
			pass
				
	#build the parser tree
	value = cap_str_value.value = value[pos:]

	for pos in range(len(value)):
		if value[pos] == '\\':
			pass
	
	return {parts[0]:cap_str_value}


if __name__ == '__main__':
	import read_termcap
	cap_str = read_termcap.get_entry(sys.argv[1], 'xterm-color')

	cap = parse_cap(cap_str)
	print cap.flags, cap.cmds

	cap = parse_cap(":cm=1.3*\E")
	print cap.flags, cap.cmds

	cap = parse_cap(":cm=1a.a.3*\E")
	print cap.flags, cap.cmds
		
		
		
		

