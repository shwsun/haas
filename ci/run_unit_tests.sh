#!/usr/bin/env bash
# On SQLite we run the tests in parallel. This speeds things up
# substantially, but is currently only safe for sqlite, since it
# uses an in memory (and  therefore per-process) database.

# Temporarily disabled till we figure out how to solve https://github.com/CCI-MOC/haas/issues/577
# if [ $DB = sqlite ]; then
#     extra_flags='-n auto'
# fi

py.test $extra_flags tests/unit tests/stress.py
