#!/bin/sh
# Same checks as CI. Used by the pre-push hook and tests.yml.
set -eu

cd "$(dirname "$0")/../backend"

if [ -n "${PYTHON:-}" ]; then :
elif [ -n "${VIRTUAL_ENV:-}" ]; then PYTHON="$VIRTUAL_ENV/bin/python"
elif [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python
else PYTHON=python3
fi

export SECRET_KEY="${SECRET_KEY:-check-secret-key}"
export DEBUG=False
export SECURE_SSL_REDIRECT=False

"$PYTHON" manage.py check --deploy --fail-level ERROR
"$PYTHON" manage.py makemigrations --check --dry-run
"$PYTHON" manage.py test
