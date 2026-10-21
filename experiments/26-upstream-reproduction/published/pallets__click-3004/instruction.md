# Issue

**Title:** Fix rendering of Enum choices' default

## Description

This PR fix (and test) the rendering of a variety of `Enum`-based choices. Specifically their default value in the help/usgae screen.

Additionally, it adds a couple of unit tests to lock-in and document the current behavior of choices.

Refs:
 - #2911
- #2928

## Task

Modify the repository so that the issue described above is resolved. The task's test suite verifies your patch by applying it on top of the base commit `a1235aacb1be` and running the modified tests.