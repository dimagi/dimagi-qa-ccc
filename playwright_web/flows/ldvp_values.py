"""Per-run values for the LDVP end-to-end test (CCCT-2670).

Everything a run types or looks for is derived from one timestamp, so a re-run
can never match the previous run's opportunity or visit rows, and the web half
and the device half provably use the same values.
"""

import time
from dataclasses import dataclass, field

# Visits in the order the deliver session submits them. V1_DUP repeats V1 exactly
# (TC-DLV-004) and, as the third visit of the day, still fits the daily limit of
# 3 - Connect checks the limit before duplicates and counts duplicates toward it.
# V3 is the fourth, over the limit (TC-DLV-005).
VISIT_KEYS = ("V1", "V2", "V1_DUP", "V3")


@dataclass
class LdvpRun:
    stamp: str
    opportunity_suffix: str
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
        opportunity_suffix=time.strftime("%y%m%d%H%M", time.localtime(now)),
        visits=visits,
    )


def expected_earned(approved, unit_amount):
    """What the worker should have earned: only approved visits are paid."""
    return approved * unit_amount
