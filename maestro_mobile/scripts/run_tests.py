import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

FLOWS_DIR = Path(__file__).parent.parent / "flows"
TEST_DATA_FILE = Path(__file__).parent.parent / "test_data" / "mobile_test_data.yaml"

FLOW_BY_CASE = {
    "TC_1": "login_signup_success.yaml",
    "TC_2": "login_account_locked.yaml",
    # Personal ID - Traditional App Install & Login (PID_48-55). All share the
    # PID_TRADITIONAL_LINK test-data entry.
    "PID_48": "pid_48_link_prompt.yaml",
    "PID_49": "pid_49_link_declined.yaml",
    "PID_51": "pid_51_link_accepted.yaml",
    "PID_53": "pid_53_unlink_prompt.yaml",
    "PID_54": "pid_54_unlink_accepted.yaml",
    "PID_55": "pid_55_unlink_declined.yaml",
}

# Cases that read the shared PID_TRADITIONAL_LINK entry rather than one keyed by
# the case id.
DATA_KEY_BY_CASE = {c: "PID_TRADITIONAL_LINK" for c in FLOW_BY_CASE if c.startswith("PID_")}

# Optional environment overrides for individual data fields (e.g. to run against
# a different worker without editing the yaml). Falls back to the yaml value.
ENV_OVERRIDE = {"mw_password": "MW_PASSWORD"}


def load_test_data(case_key):
    with open(TEST_DATA_FILE) as f:
        data = yaml.safe_load(f)
    return data[DATA_KEY_BY_CASE.get(case_key, case_key)]


def build_env_args(data):
    """One -e KEY=value per data field (keys upper-cased to match the flows).
    An ENV_OVERRIDE env var, when set, wins over the yaml value for that field."""
    args = []
    for key, value in data.items():
        env_var = ENV_OVERRIDE.get(key)
        if env_var and os.getenv(env_var):
            value = os.getenv(env_var)
        args += ["-e", f"{key.upper()}={value}"]
    return args


def run_flow(case_key):
    data = load_test_data(case_key)
    flow_file = FLOWS_DIR / FLOW_BY_CASE[case_key]

    maestro_path = shutil.which("maestro")
    if not maestro_path:
        sys.exit("maestro CLI not found on PATH. See maestro_mobile/README.md for install instructions.")

    cmd = [maestro_path, "test", str(flow_file), *build_env_args(data)]
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run Connect Maestro mobile flows locally")
    parser.add_argument("case", choices=sorted(FLOW_BY_CASE), help="Test case key to run, e.g. PID_48")
    args = parser.parse_args()

    sys.exit(run_flow(args.case))


if __name__ == "__main__":
    main()
