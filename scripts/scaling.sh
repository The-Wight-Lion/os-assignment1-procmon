#!/usr/bin/env bash
# Workload-scaling experiment: N children of fixed CPU work vs N sleeping children,
# concurrent vs sequential, 3 repetitions each. Output CSV on stdout.
cd "$(dirname "$0")/.." || exit 1
echo "workload,n,mode,run,seconds"
for kind in "work 2000" "sleep 1"; do
  for n in 1 2 4 8; do
    args=(); for i in $(seq "$n"); do args+=("./bin/workload $kind"); done
    for mode in concurrent sequential; do
      flag=""; [ $mode = sequential ] && flag="-s"
      for r in 1 2 3; do
        s=$(date +%s.%N); ./bin/procmon $flag -l /tmp/scale.log "${args[@]}" >/dev/null; e=$(date +%s.%N)
        echo "${kind%% *},$n,$mode,$r,$(echo "$e - $s" | bc)"
      done
    done
  done
done
