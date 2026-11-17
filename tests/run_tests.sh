#!/usr/bin/env bash
# Automated test suite for procmon
# Author: MD. Mohiuddin Farazi (Hibbu), ID 2403021
cd "$(dirname "$0")/.." || exit 1
P=./bin/procmon; W=./bin/workload; mkdir -p logs
pass=0; fail=0

check() {   # check <name> <logfile> <grep-pattern>
    if grep -qE "$3" "$2"; then echo "PASS  $1"; pass=$((pass+1))
    else echo "FAIL  $1"; fail=$((fail+1)); fi
}

# 1 normal case: successful exit code 0
$P -l logs/t1.log "$W exit 0" >/dev/null
check "T1 normal exit (code 0)"            logs/t1.log "EXITED .*exit code=0"
# 2 normal case: non-zero exit code is collected
$P -l logs/t2.log "$W exit 42" >/dev/null
check "T2 exit status collected (42)"      logs/t2.log "exit code=42"
# 3 failure: program does not exist
$P -l logs/t3.log "./no_such_program" >/dev/null
check "T3 exec failure detected"           logs/t3.log "EXEC_FAIL.*No such file"
# 4 failure: segmentation fault
$P -l logs/t4.log "$W segv" >/dev/null
check "T4 SIGSEGV detected"                logs/t4.log "signal 11"
# 5 failure: abort
$P -l logs/t5.log "$W abort" >/dev/null
check "T5 SIGABRT detected"                logs/t5.log "signal 6"
# 6 challenge: timeout with SIGTERM
$P -t 1 -l logs/t6.log "$W sleep 10" >/dev/null
check "T6 timeout -> SIGTERM"              logs/t6.log "signal 15 .*TIMEOUT"
# 7 challenge: child ignores SIGTERM -> SIGKILL
$P -t 1 -g 0.5 -l logs/t7.log "$W hang" >/dev/null
check "T7 escalation to SIGKILL"           logs/t7.log "signal 9 .*TIMEOUT"
# 8 boundary: child finishes just under limit is NOT killed
$P -t 2 -l logs/t8.log "$W sleep 1" >/dev/null
check "T8 under limit not killed"          logs/t8.log "EXITED .*exit code=0"
# 9 boundary: empty command string
$P -l logs/t9.log "" >/dev/null
check "T9 empty command rejected"          logs/t9.log "EXEC_FAIL"
# 10 PPID of each child equals supervisor PID
$P -l logs/t10.log "$W exit 0" "$W exit 0" >/dev/null
sup=$(grep START logs/t10.log | grep -oE " pid=[0-9]+" | cut -d= -f2)
check "T10 child ppid == supervisor pid"   logs/t10.log "CREATED .*ppid=$sup "
# 11 no zombies remain
$P -l logs/t11.log "$W exit 0" "$W segv" "$W exit 3" >/dev/null
check "T11 all children reaped"            logs/t11.log "all 3 children reaped"
# 12 invalid option
if $P -x 2>/dev/null; then echo "FAIL  T12 invalid option"; fail=$((fail+1))
else echo "PASS  T12 invalid option rejected"; pass=$((pass+1)); fi

# 13 Ctrl+C: SIGINT to procmon must stop a child that ignores SIGTERM (no hang)
$P -g 0.5 -l logs/t13.log "$W hang" >/dev/null & pp=$!
sleep 0.5; kill -INT $pp
for _ in $(seq 50); do kill -0 $pp 2>/dev/null || break; sleep 0.1; done
if kill -0 $pp 2>/dev/null; then
    kill -9 $pp 2>/dev/null; pkill -9 -f "workload hang" 2>/dev/null
    echo "FAIL T13 Ctrl+C escalates to SIGKILL"; fail=$((fail+1))
else
    check "T13 Ctrl+C escalates to SIGKILL" logs/t13.log "KILL"
fi
wait $pp 2>/dev/null

# 14 no zombie child is left while procmon is still running
$P -l logs/t14.log "$W exit 0" "$W sleep 2" >/dev/null & pp=$!
sleep 1
if ps --ppid $pp -o stat= | grep -q '^Z'; then echo "FAIL T14 no zombie while running"; fail=$((fail+1))
else echo "PASS  T14 no zombie while running"; pass=$((pass+1)); fi
wait $pp 2>/dev/null

echo "----------------------------------------"
echo "Passed: $pass   Failed: $fail"
[ $fail -eq 0 ]
