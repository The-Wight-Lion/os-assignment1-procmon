#!/usr/bin/env bash
# Builds the project, runs the tests and all experiments, and stores the REAL
# terminal output of this machine in evidence/ and logs/.
cd "$(dirname "$0")/.." || exit 1
mkdir -p evidence logs screenshots

for tool in gcc make pstree pgrep bc; do
    command -v "$tool" >/dev/null || { echo "missing: $tool  (sudo apt install build-essential psmisc procps bc)"; exit 1; }
done

make clean >/dev/null
{ echo '$ make'; make 2>&1; } > evidence/build.txt
cat evidence/build.txt

# environment table (used by the report)
{
  echo "Operating system|$(. /etc/os-release; echo "$PRETTY_NAME")"
  echo "Linux kernel|$(uname -r) $(uname -m)"
  echo "CPU|$(lscpu | awk -F: '/Model name/ {gsub(/^ +/,"",$2); print $2; exit}')"
  echo "CPU cores available|$(nproc)"
  echo "Compiler|$(gcc --version | head -1)"
  echo "Editor|Visual Studio Code"
  echo "Tools|$(make --version | head -1), ps (procps), pstree (psmisc), bc"
} > evidence/env.txt

{ echo '$ make test'; make test 2>&1; } > evidence/tests.txt
cat evidence/tests.txt

echo "== experiments =="
./scripts/run_experiments.sh
echo "== scaling (takes ~2-3 minutes) =="
./scripts/scaling.sh > evidence/scaling.csv
echo "done. Now take screenshots into screenshots/ and run: python3 report/make_report.py"
