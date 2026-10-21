# Issue

**Title:** dict datastructures could include `|` and `|=` behavior

## Description

Python 3.9 added two operators to dict:

* `a | b` does `{*a, *b}`
* `a |= b` does `a.update(b)`

Implement this for our various dict datastructures (assuming it makes sense in each case).

## Task

Modify the repository so that the issue described above is resolved. The task's test suite verifies your patch by applying it on top of the base commit `862cb193c2b1` and running the modified tests.