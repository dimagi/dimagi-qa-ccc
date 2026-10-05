#!/usr/bin/env bash
# Run a command so that a cancelled job actually reaches it.
#
#   exec .github/scripts/forward_signals.sh '<command line>'
#
# The `exec` matters: the runner signals only the step's own shell process. Run
# without it, this script is a child of that shell and never hears the signal -
# a cancelled test run on 2026-10-05 (run 37315241026) left build 332038cc
# running exactly that way.
#
# When a job is cancelled (a superseding push, a manual cancel, a timeout) the
# runner sends SIGINT to the step's shell, SIGTERM 7.5s later, then kills it.
# Bash does not pass those on to the command it is waiting for, so the Python
# behind it - run_on_browserstack.py, or pytest under xvfb-run for the hybrid
# tests - never learns it is being cancelled, and never stops its BrowserStack
# build. That build then keeps driving the shared fixture accounts while the
# next run starts on them.
#
# So the command runs in its own process group, and both signals are forwarded
# to the whole group: python, tee, xvfb-run and anything else in the pipeline.
# The command's exit status is this script's exit status. Use `tee -i` in the
# command so the log keeps receiving the stop-build output after the interrupt.
set -u

# Python block-buffers stdout into a pipe, so a cancelled step used to lose
# everything it had printed, the stop-build lines included.
export PYTHONUNBUFFERED=1

setsid bash -o pipefail -c "$1" &
pid=$!
forward() { kill -"$1" -- -"$pid" 2>/dev/null; }
trap 'forward INT' INT
trap 'forward TERM' TERM

# A trapped signal makes `wait` return early (status > 128) while the command is
# still running, so keep waiting until it has really exited.
wait "$pid"
status=$?
while kill -0 "$pid" 2>/dev/null; do
  wait "$pid"
  status=$?
done
exit "$status"
