#! /bin/bash -e

BASE=$(dirname "$0")
ROOT=$(dirname "$BASE")

PYTHON2="$ROOT/.venv2/bin/python"
PYTHON3="$ROOT/.venv3/bin/python"

[ ! -f $PYTHON2 ] && { "$PYTHON2"; exit 1; }
[ ! -f $PYTHON3 ] && { "$PYTHON3"; exit 1; }

echo "Starting Python 2->{2,3} tests"
$PYTHON2 -m pytest "$@"

echo "Starting Python 3->{2,3} tests"
$PYTHON3 -m pytest "$@"
