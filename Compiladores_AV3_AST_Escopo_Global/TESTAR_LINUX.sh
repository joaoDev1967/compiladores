#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONIOENCODING=utf-8
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    printf 'Erro: Python 3 não foi encontrado. Instale Python 3 e tente novamente.\n' >&2
    exit 127
fi

"$PYTHON" -m unittest discover -s tests -t . -v
exit "$?"
