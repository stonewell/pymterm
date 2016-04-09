import os
import sys

class Cap:
	def __init__(self):
		self.flags = {}
		self.cmds = {}
		self.control_data_start_state = ControlDataState()
		
def parse_cap(cap_str):
	cap = Cap()
	
	for field in cap_str.split(':'):
		if len(field) == 0:
			continue

		if field.find('=') > 0:
			cap.cmds.update(parse_str_cap(field, cap.control_data_start_state))
		elif field.find('#') > 0:
			parts = field.split('#')
			cap.flags.update({parts[0]:int(parts[1])})
		else:
			cap.flags.update({field:1})

	return cap

class ControlDataState:
	def __init__(self):
		self.cap_name = ''
		self.next_states = {}
		self.increase = False
		self.digit_state = None

	def add_state(self, c, state):
		if c in self.next_states:
			return self.next_states[c]

		self.next_states[c] = state
		return state

	def add_digit_state(self, state):
		if self.digit_state:
			return self.digit_state

		self.digit_state = state
		return state

	def handle(self, c):
		pass

class DigitState(ControlDataState):
	def __init__(self):
		ControlDataState.__init__(self)
		self.digit_base = 10
		
class CapStringValue:
	def __init__(self):
		self.padding = 0.0
		self.value = ''
		self.name = ''

	def __str__(self):
		return ','.join([self.name, str(self.padding), self.value])

	def __repr__(self):
		return self.__str__()
                
def parse_padding(value):
	padding = 0.0
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
		except ValueError:
			pass

	return (pos, padding)

def build_parser_state_machine(cap_str_value, start_state):
	value = cap_str_value.value

	pos = 0
	
	cur_state = start_state
	repeat_state = None
	repeat_char = None
	is_repeat_state = False
	increase_param = False
	is_digit_state = False
	digit_base = 10
	
	while pos <len(value):
		c = value[pos]
		
		if c == '\\':
			pos += 1

			if pos >= len(value):
				raise ValueError("Unterminaled str")
			
			c = value[pos]
			if c == 'E':
				c = chr(0x1B)
			elif c == '\\':
				c = '\\'
			elif c == '(':
				is_repeat_state = True
				pos += 1
				continue
			elif c == ')':
				if not repeat_state or not repeat_char:
					raise ValueError("Invalid repeat state:" + str(pos) + "," + value)

				cur_state.add_state(repeat_char, repeat_state)
				
				repeat_char = None
				repeat_state = None
				is_repeat_state = False
				pos += 1
				continue
			elif c.isdigit():
				v = 0
				while pos < len(value) and c.isdigit():
					v = v * 8 + int(c)
					pos += 1
					if pos < len(value):
						c = value[pos]

				if not c.isdigit():
					pos -= 1
					
				c = chr(v)
			else:
				raise ValueError("unknown escape string:" + c + "," + str(pos) + "," + value)
		elif c == '%':
			pos += 1

			if pos >= len(value):
				raise ValueError("Unterminaled str")
			
			c = value[pos]

			if c == '%':
				c = '%'
			elif c == 'i':
				increase_param = True
				pos += 1
				continue
			elif c == 'd':
				is_digit_state = True
				digit_base = 10
			elif c == 'X' or c == 'x':
				is_digit_state = True
				digit_base = 16
			else:
				raise ValueError('unknown format string:' + c + "," + str(pos) + "," + value)

		#build state with c
		if is_digit_state:
			cur_state = cur_state.add_digit_state(DigitState())
			cur_state.digit_base = digit_base
		else:
			cur_state = cur_state.add_state(c, ControlDataState())

		if is_repeat_state and not repeat_state:
			repeat_state = cur_state
			repeat_char = c

		is_digit_state = False
			
		pos += 1
		
                
def parse_str_cap(field, start_state):
	cap_str_value = CapStringValue()
	
	parts = field.split('=')

	cap_str_value.name = parts[0]
	value = cap_str_value.value = '='.join(parts[1:])

	#padding
	pos, cap_str_value.padding = parse_padding(value)
				
	#build the parser state machine
	value = cap_str_value.value = value[pos:]

	build_parser_state_machine(cap_str_value, start_state)
	
	return {parts[0]:cap_str_value}

if __name__ == '__main__':
	import read_termdata
	cap_str = read_termdata.get_entry(sys.argv[1], 'xterm-256color')

	cap = parse_cap(cap_str)
	print cap.flags, cap.cmds
	
	cap = parse_cap(":cm=1.3*\E")
	print cap.flags, cap.cmds

	cap = parse_cap(":cm=1a.a.3*\E")
	print cap.flags, cap.cmds
		
		
		
		

