"""PyInstaller entry script.

A frozen entry script runs as a top-level module, so `ytdlp_qt/__main__.py`
cannot be used directly — its relative imports would have no parent package.
This shim imports the package properly instead.
"""

from ytdlp_qt.__main__ import main

raise SystemExit(main())
