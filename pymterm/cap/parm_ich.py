import os
import sys


def handle(term, context, cap_turple):
	cap_name, increase = cap_turple

	if increase:
		for idx in range(len(context.params)):
			context.params[idx] -= 1 if context.params[idx] != 0 else 0

	term.output_normal_data(' ' * context.params[0], True)

