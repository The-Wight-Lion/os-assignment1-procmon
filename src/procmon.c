/*
 * procmon.c - Linux process-monitoring program
 *
 * Course   : Operating Systems - Assignment 1 (Topic 1)
 * Topic    : Process creation, execution, supervision and termination
 * Author   : MD. Mohiuddin Farazi (Hibbu), ID 2403021
 *
 * What it does
 *   For every command given on the command line the parent process:
 *     1. creates a child with fork()
 *     2. the child replaces its image with execvp()
 *     3. the parent supervises all children with waitpid(WNOHANG)
 *     4. collects the exit status (normal exit / killed by signal)
 *     5. detects exec() failure through a close-on-exec pipe
 *     6. kills a child (and only its own child) when it exceeds a timeout
 *     7. writes a timestamped lifecycle log of every event
 *
 * Usage
 *   procmon [-t seconds] [-g grace] [-l logfile] [-s] "cmd args" ["cmd args" ...]
 *     -t  execution limit per child in seconds (0 = no limit, default 0)
 *     -g  grace period between SIGTERM and SIGKILL (default 1 s)
 *     -l  lifecycle log file (default: procmon.log)
 *     -s  run children sequentially instead of concurrently
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define MAX_CHILDREN 64
#define MAX_ARGS     32
#define POLL_MS      20

/* Possible states of a supervised child (mirrors the OS process states
 * that are visible to the parent). */
typedef enum { ST_RUNNING, ST_EXITED, ST_SIGNALED, ST_EXEC_FAILED } cstate_t;

typedef struct {
    pid_t           pid;
    char            cmd[256];
    struct timespec start;          /* time of fork()                    */
    struct timespec end;            /* time the parent reaped the child  */
    cstate_t        state;
    int             code;           /* exit code or signal number        */
    int             exec_errno;     /* errno reported by failed exec     */
    int             errpipe;        /* read end of the exec-status pipe  */
    int             term_sent;      /* SIGTERM already sent (timeout)    */
    int             timed_out;
    double          term_run;       /* run time (s) when SIGTERM was sent */
} child_t;

static child_t children[MAX_CHILDREN];
static int     nchildren;
static FILE   *logfp;
static double  timeout_s = 0.0;
static double  grace_s   = 1.0;
static volatile sig_atomic_t interrupted = 0;

/* ---------- time helpers ---------------------------------------------- */
static double ts_diff(const struct timespec *a, const struct timespec *b)
{
    return (double)(b->tv_sec - a->tv_sec) + (b->tv_nsec - a->tv_nsec) / 1e9;
}

static void wall_stamp(char *buf, size_t n)
{
    struct timespec ts;
    struct tm tm;
    clock_gettime(CLOCK_REALTIME, &ts);
    localtime_r(&ts.tv_sec, &tm);
    size_t len = strftime(buf, n, "%Y-%m-%d %H:%M:%S", &tm);
    snprintf(buf + len, n - len, ".%03ld", ts.tv_nsec / 1000000);
}

/* ---------- lifecycle log --------------------------------------------- */
/* Every event goes both to stdout and to the log file, one line each:
 * <timestamp> | <EVENT> | pid=<pid> ppid=<ppid> | <details>            */
static void log_event(const char *event, pid_t pid, pid_t ppid, const char *fmt, ...)
{
    char stamp[64], msg[512];
    va_list ap;
    wall_stamp(stamp, sizeof stamp);
    va_start(ap, fmt);
    vsnprintf(msg, sizeof msg, fmt, ap);
    va_end(ap);
    printf("%s | %-10s | pid=%-6d ppid=%-6d | %s\n", stamp, event, pid, ppid, msg);
    fflush(stdout);
    if (logfp) {
        fprintf(logfp, "%s | %-10s | pid=%-6d ppid=%-6d | %s\n", stamp, event, pid, ppid, msg);
        fflush(logfp);
    }
}

/* ---------- split a command string into argv -------------------------- */
static int split_args(char *s, char **argv)
{
    int argc = 0;
    for (char *tok = strtok(s, " \t"); tok && argc < MAX_ARGS - 1; tok = strtok(NULL, " \t"))
        argv[argc++] = tok;
    argv[argc] = NULL;
    return argc;
}

/* ---------- create one child ------------------------------------------ */
static int spawn(const char *cmdline)
{
    if (nchildren >= MAX_CHILDREN) {
        fprintf(stderr, "procmon: too many children (max %d)\n", MAX_CHILDREN);
        return -1;
    }
    child_t *c = &children[nchildren];
    memset(c, 0, sizeof *c);
    snprintf(c->cmd, sizeof c->cmd, "%s", cmdline);

    /* Pipe used only to report exec() failure. The write end is marked
     * close-on-exec: if exec succeeds it closes automatically and the
     * parent reads EOF (0 bytes); if exec fails the child writes errno. */
    int pfd[2];
    if (pipe2(pfd, O_CLOEXEC) == -1) {
        perror("procmon: pipe2");
        return -1;
    }

    clock_gettime(CLOCK_MONOTONIC, &c->start);
    pid_t pid = fork();
    if (pid == -1) {                                   /* fork failed */
        log_event("FORK_FAIL", -1, getpid(), "cmd=\"%s\" error=%s", cmdline, strerror(errno));
        close(pfd[0]); close(pfd[1]);
        return -1;
    }

    if (pid == 0) {                                    /* ---- child ---- */
        close(pfd[0]);
        /* Own process group: lets the parent terminate the child and any
         * grandchildren it creates, without touching unrelated processes. */
        setpgid(0, 0);
        signal(SIGINT, SIG_DFL);
        signal(SIGTERM, SIG_DFL);

        char buf[256], *argv[MAX_ARGS];
        snprintf(buf, sizeof buf, "%s", cmdline);
        if (split_args(buf, argv) == 0) {
            int e = EINVAL;
            if (write(pfd[1], &e, sizeof e) < 0) { /* nothing more we can do */ }
            _exit(127);
        }
        execvp(argv[0], argv);
        /* Only reached if exec failed */
        int e = errno;
        if (write(pfd[1], &e, sizeof e) < 0) { /* ignore */ }
        _exit(127);
    }

    /* ---- parent ---- */
    setpgid(pid, pid);              /* avoid race with child's own setpgid */
    close(pfd[1]);
    c->pid     = pid;
    c->state   = ST_RUNNING;
    c->errpipe = pfd[0];
    nchildren++;
    log_event("CREATED", pid, getpid(), "cmd=\"%s\"", cmdline);

    /* Find out whether exec succeeded (blocks only until exec or _exit) */
    int e;
    ssize_t r;
    do { r = read(c->errpipe, &e, sizeof e); } while (r == -1 && errno == EINTR);
    close(c->errpipe);
    if (r == (ssize_t)sizeof e) {
        c->exec_errno = e;
        log_event("EXEC_FAIL", pid, getpid(), "cmd=\"%s\" error=%s", cmdline, strerror(e));
    } else {
        log_event("EXEC_OK", pid, getpid(), "program image replaced by \"%s\"", cmdline);
    }
    return 0;
}

/* ---------- interpret status returned by waitpid ----------------------- */
static void record_exit(child_t *c, int status)
{
    clock_gettime(CLOCK_MONOTONIC, &c->end);
    double dur = ts_diff(&c->start, &c->end);

    if (c->exec_errno) {
        c->state = ST_EXEC_FAILED;
        c->code  = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
        log_event("REAPED", c->pid, getpid(),
                  "exec failed (%s), exit code=%d, duration=%.3fs",
                  strerror(c->exec_errno), c->code, dur);
    } else if (WIFEXITED(status)) {
        c->state = ST_EXITED;
        c->code  = WEXITSTATUS(status);
        log_event("EXITED", c->pid, getpid(),
                  "normal termination, exit code=%d, duration=%.3fs", c->code, dur);
    } else if (WIFSIGNALED(status)) {
        c->state = ST_SIGNALED;
        c->code  = WTERMSIG(status);
        log_event("SIGNALED", c->pid, getpid(),
                  "abnormal termination by signal %d (%s)%s%s, duration=%.3fs",
                  c->code, strsignal(c->code),
                  WCOREDUMP(status) ? ", core dumped" : "",
                  c->timed_out ? " [TIMEOUT]" : "", dur);
    }
}

/* ---------- timeout mechanism (challenge) ------------------------------ */
static double run_time(const child_t *c)
{
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return ts_diff(&c->start, &now);
}

/* Stage 1: run time > limit  -> SIGTERM to the child's process group.
 * Stage 2: still alive grace_s after SIGTERM -> SIGKILL (cannot be ignored).
 * Stage 2 also applies after Ctrl+C, so a child that ignores SIGTERM
 * cannot make procmon hang. */
static void check_timeout(child_t *c)
{
    if (c->state != ST_RUNNING) return;
    double run = run_time(c);

    if (!c->term_sent && timeout_s > 0 && run > timeout_s) {
        c->term_sent = 1;
        c->timed_out = 1;
        c->term_run  = run;
        log_event("TIMEOUT", c->pid, getpid(),
                  "ran %.2fs > limit %.2fs, sending SIGTERM to group %d", run, timeout_s, c->pid);
        /* negative pid = the child's own process group (child + its descendants) */
        if (kill(-c->pid, SIGTERM) == -1 && errno != ESRCH)
            perror("procmon: kill SIGTERM");
    } else if (c->term_sent == 1 && run > c->term_run + grace_s) {
        log_event("KILL", c->pid, getpid(),
                  "still alive after %.2fs grace, sending SIGKILL", grace_s);
        if (kill(-c->pid, SIGKILL) == -1 && errno != ESRCH)
            perror("procmon: kill SIGKILL");
        c->term_sent = 2;   /* SIGKILL sent: do not repeat */
    }
}

/* ---------- supervise until every child is reaped ---------------------- */
static void supervise(void)
{
    int running;
    do {
        running = 0;
        for (int i = 0; i < nchildren; i++) {
            child_t *c = &children[i];
            if (c->state != ST_RUNNING) continue;
            int status;
            pid_t r = waitpid(c->pid, &status, WNOHANG);
            if (r == c->pid) {
                record_exit(c, status);
            } else if (r == 0) {
                running++;
                check_timeout(c);
                if (interrupted && !c->term_sent) {   /* Ctrl+C: stop our children only */
                    c->term_sent = 1;
                    c->term_run  = run_time(c);
                    log_event("INTERRUPT", c->pid, getpid(), "forwarding SIGTERM to child group");
                    kill(-c->pid, SIGTERM);
                }
            } else if (r == -1 && errno != EINTR) {
                perror("procmon: waitpid");
                c->state = ST_EXITED;
            }
        }
        if (running) {
            struct timespec d = { 0, POLL_MS * 1000000L };
            nanosleep(&d, NULL);
        }
    } while (running);
}

static void on_sigint(int sig) { (void)sig; interrupted = 1; }

static void usage(const char *p)
{
    fprintf(stderr,
        "Usage: %s [-t seconds] [-g grace] [-l logfile] [-s] \"cmd args\" ...\n"
        "  -t  per-child execution limit (0 = none)\n"
        "  -g  grace period between SIGTERM and SIGKILL (default 1)\n"
        "  -l  lifecycle log file (default procmon.log)\n"
        "  -s  run children sequentially\n", p);
}

/* ---------- summary table --------------------------------------------- */
static void summary(void)
{
    static const char *names[] = { "RUNNING", "EXITED", "SIGNALED", "EXEC_FAIL" };
    printf("\n%-7s %-34s %-10s %-6s %-9s\n", "PID", "COMMAND", "RESULT", "CODE", "TIME(s)");
    printf("------- ---------------------------------- ---------- ------ ---------\n");
    for (int i = 0; i < nchildren; i++) {
        child_t *c = &children[i];
        printf("%-7d %-34.34s %-10s %-6d %-9.3f%s\n", c->pid, c->cmd, names[c->state],
               c->code, ts_diff(&c->start, &c->end), c->timed_out ? " timeout" : "");
    }
}

int main(int argc, char *argv[])
{
    const char *logpath = "procmon.log";
    int sequential = 0, opt;

    while ((opt = getopt(argc, argv, "t:g:l:sh")) != -1) {
        switch (opt) {
        case 't': timeout_s = atof(optarg); break;
        case 'g': grace_s   = atof(optarg); break;
        case 'l': logpath   = optarg;       break;
        case 's': sequential = 1;           break;
        default : usage(argv[0]); return 2;
        }
    }
    if (optind >= argc) { usage(argv[0]); return 2; }
    if (timeout_s < 0 || grace_s < 0) {
        fprintf(stderr, "procmon: time values must be non-negative\n");
        return 2;
    }

    logfp = fopen(logpath, "w");
    if (!logfp) { perror("procmon: cannot open log file"); return 1; }

    struct sigaction sa = { 0 };
    sa.sa_handler = on_sigint;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGINT, &sa, NULL);

    log_event("START", getpid(), getppid(), "procmon supervisor started, timeout=%.2fs, mode=%s",
              timeout_s, sequential ? "sequential" : "concurrent");

    for (int i = optind; i < argc && !interrupted; i++) {
        if (spawn(argv[i]) == 0 && sequential)
            supervise();
    }
    supervise();
    log_event("FINISH", getpid(), getppid(), "all %d children reaped, no zombies left", nchildren);
    summary();

    fclose(logfp);
    /* non-zero if any child failed */
    for (int i = 0; i < nchildren; i++)
        if (children[i].state != ST_EXITED || children[i].code != 0) return 1;
    return 0;
}
