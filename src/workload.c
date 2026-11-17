/*
 * workload.c - test workloads executed by procmon's children
 * Author: MD. Mohiuddin Farazi (Hibbu), ID 2403021
 *
 *   workload cpu   <sec>     busy CPU loop for <sec> seconds
 *   workload work  <M>       fixed CPU work: <M> million loop iterations
 *   workload sleep <sec>     sleep (blocked state) for <sec> seconds
 *   workload exit  <code>    exit immediately with <code>
 *   workload segv            dereference NULL -> SIGSEGV
 *   workload abort           call abort()      -> SIGABRT
 *   workload kill  <sig>     send <sig> to itself
 *   workload tree  <n> <sec> fork <n> grandchildren that sleep <sec>
 *   workload hang            ignore SIGTERM and loop forever (tests SIGKILL)
 */
#define _GNU_SOURCE
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static double now(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}

int main(int argc, char *argv[])
{
    if (argc < 2) {
        fprintf(stderr, "usage: workload cpu|work|sleep|exit|segv|abort|kill|tree|hang [arg]\n");
        return 2;
    }
    const char *m = argv[1];
    double a = argc > 2 ? atof(argv[2]) : 1;
    printf("    [workload] mode=%s pid=%d ppid=%d\n", m, getpid(), getppid());
    fflush(stdout);

    if (!strcmp(m, "cpu")) {
        volatile unsigned long x = 0;
        double end = now() + a;
        while (now() < end) x++;
        return 0;
    } else if (!strcmp(m, "work")) {
        volatile unsigned long x = 0;
        unsigned long n = (unsigned long)(a * 1e6);
        for (unsigned long i = 0; i < n; i++) x += i;
        return 0;
    } else if (!strcmp(m, "sleep")) {
        struct timespec d = { (time_t)a, (long)((a - (time_t)a) * 1e9) };
        nanosleep(&d, NULL);
        return 0;
    } else if (!strcmp(m, "exit")) {
        return (int)a;
    } else if (!strcmp(m, "segv")) {
        volatile int *p = NULL;
        *p = 1;
    } else if (!strcmp(m, "abort")) {
        abort();
    } else if (!strcmp(m, "kill")) {
        raise((int)a);
        return 0;
    } else if (!strcmp(m, "tree")) {
        int n = (int)a;
        int s = argc > 3 ? atoi(argv[3]) : 3;
        for (int i = 0; i < n; i++) {
            pid_t p = fork();
            if (p == -1) { perror("fork"); return 1; }
            if (p == 0) {
                printf("    [grandchild] pid=%d ppid=%d\n", getpid(), getppid());
                fflush(stdout);
                sleep(s);
                _exit(0);
            }
        }
        while (wait(NULL) > 0) ;
        return 0;
    } else if (!strcmp(m, "hang")) {
        signal(SIGTERM, SIG_IGN);
        for (;;) pause();
    }
    fprintf(stderr, "workload: unknown mode %s\n", m);
    return 2;
}
