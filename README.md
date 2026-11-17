# procmon – Process Management and Command Execution in Linux

**Course:** Operating Systems – Assignment 1 (Topic 1)
**Student:** MD. Mohiuddin Farazi (Hibbu) – ID 2403021
**Topic number:** A = ((2403021 mod 10) − 1) mod 5 + 1 = ((1 − 1) mod 5) + 1 = **1**

`procmon` is a small Linux supervisor written in C. For every command it is given it
creates a child with `fork()`, replaces the child image with `execvp()`, watches the
child with `waitpid()`, collects the exit status, and writes a timestamped lifecycle log.
It detects `exec` failures, crashes (signals) and enforces an optional execution timeout.

## Directory layout

```
procmon/
├── src/procmon.c          supervisor (fork / exec / waitpid / timeout / log)
├── src/workload.c         test workloads (cpu, work, sleep, exit, segv, abort, kill, tree, hang)
├── tests/run_tests.sh     automated test suite (14 tests)
├── scripts/run_experiments.sh  experiments + ps/pstree capture
├── scripts/scaling.sh     timing experiment (CSV output)
├── evidence/              captured terminal output
├── logs/                  lifecycle logs
└── Makefile
```

## Dependencies

* Ubuntu 22.04/24.04 (any Linux with glibc)
* `gcc`, `make`, `procps` (`ps`), `psmisc` (`pstree`), `bc`

```bash
sudo apt update && sudo apt install build-essential psmisc bc
```

## Build and run

```bash
make                 # builds bin/procmon and bin/workload
make test            # runs the 14-test suite
./scripts/run_experiments.sh
```

## Usage

```
./bin/procmon [-t seconds] [-g grace] [-l logfile] [-s] "cmd args" ["cmd args" ...]
  -t  per-child execution limit in seconds (0 = no limit)
  -g  grace period between SIGTERM and SIGKILL (default 1 s)
  -l  lifecycle log file (default procmon.log)
  -s  run children one after another (sequential)
```

Examples

```bash
./bin/procmon "ls -l" "./bin/workload sleep 2" "./bin/workload segv"
./bin/procmon -t 2 "./bin/workload cpu 10" "./bin/workload hang"
```

While it runs, observe it from a second terminal:

```bash
ps -o pid,ppid,pgid,stat,etime,cmd --ppid $(pgrep -n procmon)
pstree -p -a $(pgrep -n procmon)
```

## Log format

```
<YYYY-MM-DD HH:MM:SS.mmm> | <EVENT> | pid=<pid> ppid=<ppid> | <details>
```
Events: `START, CREATED, EXEC_OK, EXEC_FAIL, FORK_FAIL, EXITED, SIGNALED, REAPED, TIMEOUT, KILL, INTERRUPT, FINISH`.

## Limitations

* Commands are split on spaces only; quoting and shell features (pipes, `>`, globbing) are not supported.
* Supervision is by polling `waitpid(WNOHANG)` every 20 ms, so timeout accuracy is ±20 ms.
* At most 64 children per run.

