"""Exact unit-cost edit distance; one-row dynamic programming."""
import sys


def distance(first, second):
    row = list(range(len(second) + 1))
    for i, left in enumerate(first, 1):
        following = [i]
        for j, right in enumerate(second, 1):
            following.append(min(following[-1] + 1, row[j] + 1,
                                 row[j - 1] + (left != right)))
        row = following
    return row[-1]


if __name__ == '__main__':
    first, second = sys.stdin.read().splitlines()
    print(distance(first, second))
