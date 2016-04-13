import os
import sys

def handle(term, context, cap_turple):
	cap_name, increase = cap_turple

	if increase:
		for idx in range(len(context.params)):
			context.params[idx] -= 1

	sys.stdout.write('\x1B%d' % context.params[0])
