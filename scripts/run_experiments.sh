#!/usr/bin/env bash
# Runs all experiments and stores terminal output in evidence/ and logs in logs/
# Author: MD. Mohiuddin Farazi (Hibbu), ID 2403021
cd "$(dirname "$0")/.." || exit 1
mkdir -p logs evidence
P=./bin/procmon; W=./bin/workload
# print the command the way it is typed (arguments with spaces in quotes), then run it
show() { local s="" a; for a in "$@"; do [[ $a == *" "* ]] && s+=" \"$a\"" || s+=" $a"; done; echo "\$${s}"; }
run() { local out=$1; shift; { show "$@"; "$@"; } > "evidence/$out" 2>&1; }

# 1. mixed workload: normal, non-zero, exec failure, crashes
run exp1.txt $P -l logs/exp1.log "$W cpu 2" "$W sleep 2" "$W exit 3" "./bin/no_such_prog" "$W segv" "$W abort"

# 2. process hierarchy observed with ps and pstree while running
run exp2.txt $P -l logs/exp2.log "$W tree 3 4" "$W cpu 4" "$W sleep 4" &
sleep 1.2; SUP=$(pgrep -n procmon)
{ echo "\$ ps -o pid,ppid,pgid,stat,etime,cmd -p $SUP --ppid $SUP"; ps -o pid,ppid,pgid,stat,etime,cmd -p $SUP --ppid $SUP
  echo; echo "\$ ps -eo pid,ppid,pgid,stat,cmd | grep workload"; ps -eo pid,ppid,pgid,stat,cmd | grep '[w]orkload'; } > evidence/ps.txt
{ echo "\$ pstree -p -a $SUP"; pstree -p -a "$SUP"; } > evidence/pstree.txt
wait

# 3. challenge: timeout (SIGTERM, then SIGKILL for a child that ignores SIGTERM)
run exp3.txt $P -t 2 -g 1 -l logs/exp3.log "$W sleep 1" "$W cpu 10" "$W hang" "$W tree 2 30"

# 4. normal termination vs termination by signal
run exp4.txt $P -l logs/exp4.log "$W exit 0" "$W exit 1" "$W kill 15" "$W kill 9" "$W kill 2" "$W segv"

# 5. sequential vs concurrent supervision (5 x 1s sleep)
for mode in "-s" ""; do
  s=$(date +%s.%N); $P $mode -l logs/exp5.log "$W sleep 1" "$W sleep 1" "$W sleep 1" "$W sleep 1" "$W sleep 1" >/dev/null
  e=$(date +%s.%N); echo "mode=${mode:-concurrent} wall=$(echo "$e - $s" | bc)"
done > evidence/exp5.txt
sed -i 's/mode=-s/mode=sequential/' evidence/exp5.txt
