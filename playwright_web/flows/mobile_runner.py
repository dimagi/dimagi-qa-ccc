"""Bridge to the Maestro BrowserStack runner so hybrid web+mobile tests can
drive a real device mid-test.

The runner lives in maestro_mobile/scripts/ (its own suite, invoked directly by
its CI workflow); this module puts it on the import path and re-exports the
pieces the Playwright suite needs.
"""

import sys

from utils.helpers import REPO_ROOT

SCRIPTS_DIR = REPO_ROOT / "maestro_mobile" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_on_browserstack import (  # noqa: E402
    apply_env_overrides,
    env_by_flow,
    resolve_worker,
    run_flows,
)

__all__ = ["apply_env_overrides", "env_by_flow", "resolve_worker", "run_flows"]
