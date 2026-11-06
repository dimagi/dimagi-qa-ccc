"""Per-run values for the LDVP end-to-end test (CCCT-2670).

Everything a run types or looks for is derived from one timestamp, so a re-run
can never match the previous run's opportunity or visit rows, and the web half
and the device half provably use the same values.
"""

import time
from dataclasses import dataclass, field

# Visits in the order the deliver session submits them. V1_DUP repeats V1 exactly
# (TC-DLV-004) and is submitted on the manual-review opportunity only; V3 is over
# the daily limit (TC-DLV-005).
VISIT_KEYS = ("V1", "V2", "V1_DUP", "V3")


@dataclass
class LdvpRun:
    stamp: str
    visits: dict = field(default_factory=dict)

    def device_env(self):
        """Maestro env values for the deliver session, one name/id pair per visit."""
        env = {}
        for key, (name, visit_id) in self.visits.items():
            env[f"VISIT_NAME_{key}"] = name
            env[f"VISIT_ID_{key}"] = visit_id
        return env


def new_run(now=None):
    now = time.time() if now is None else now
    stamp = str(int(now))[-6:]
    visits = {key: (f"LDVP-{key}-{stamp}", f"{stamp}{key[1]}") for key in VISIT_KEYS if key != "V1_DUP"}
    visits["V1_DUP"] = visits["V1"]
    return LdvpRun(
        stamp=stamp,
        visits=visits,
    )


def expected_earned(approved, unit_amount):
    """What the worker should have earned: only approved visits are paid."""
    return approved * unit_amount


def assert_percent(text, expected, column):
    """Connect renders "100.0%", so compare the number. A dash (nothing recorded
    yet) fails as an assertion, which the web waits retry."""
    try:
        value = float(text.strip().rstrip("%"))
    except ValueError:
        value = None
    assert value == expected, f"{column} reads {text!r}, expected {expected}%"
