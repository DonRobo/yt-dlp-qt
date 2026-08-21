#!/usr/bin/env bash
# Launch the app on Linux, creating a virtualenv on first run.
set -euo pipefail
cd "$(dirname "$0")"

VENV=.venv
if [ ! -d "$VENV" ]; then
    echo "Creating virtualenv…"
    # --system-site-packages lets a distro-packaged PySide6 be reused.
    python3 -m venv --system-site-packages "$VENV"
    "$VENV/bin/python" -c "import PySide6" 2>/dev/null \
        || "$VENV/bin/pip" install --quiet PySide6
fi

exec "$VENV/bin/python" -c "import sys; sys.path.insert(0, 'src'); from ytdlp_qt.__main__ import main; sys.exit(main())" "$@"
