"""Generate independent synthetic strings, not sampled or designed biological sequences."""
import random


def generate_testcase(params):
    length = params['length']
    first = ''.join(random.choice('ACGT') for _ in range(length))
    second = ''.join(random.choice('ACGT') for _ in range(length))
    return first + '\n' + second + '\n', {'first': first, 'second': second}
