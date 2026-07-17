import argparse
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
}


def load_test_data(case_key):
    with open(TEST_DATA_FILE) as f:
        data = yaml.safe_load(f)
    return data[case_key]


def run_flow(case_key):
    data = load_test_data(case_key)
    flow_file = FLOWS_DIR / FLOW_BY_CASE[case_key]

    maestro_path = shutil.which("maestro")
    if not maestro_path:
        sys.exit("maestro CLI not found on PATH. See maestro_mobile/README.md for install instructions.")

    cmd = [
        maestro_path, "test", str(flow_file),
        "-e", f"COUNTRY_CODE={data['country_code']}",
        "-e", f"PHONE_NUMBER={data['phone_number']}",
        "-e", f"USERNAME={data['username']}",
        "-e", f"BACKUP_CODE={data['backup_code']}",
    ]
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run Connect Maestro mobile flows locally")
    parser.add_argument("case", choices=sorted(FLOW_BY_CASE), help="Test case key to run, e.g. TC_1")
    args = parser.parse_args()

    sys.exit(run_flow(args.case))


if __name__ == "__main__":
    main()
