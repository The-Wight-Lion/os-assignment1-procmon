#!/usr/bin/env python3
"""Builds report/Assignment1_Report.pdf from the REAL outputs in evidence/ and logs/.

Run ./scripts/run_all.sh first, put your own screenshots (PNG) into screenshots/,
then:  python3 report/make_report.py
Needs:  pip install reportlab matplotlib   (or: sudo apt install python3-reportlab python3-matplotlib)
"""
import csv, datetime, glob, os, statistics, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, PageBreak, Paragraph, Preformatted, SimpleDocTemplate,
                                Spacer, Table, TableStyle, KeepTogether)

# ------------------------------------------------------------------ edit these
NAME = "MD. Mohiuddin Farazi (Hibbu)"
STUDENT_ID = 2403021
GITHUB_URL = "https://github.com/The-Wight-Lion/os-assignment1-procmon"
# ------------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV, LOGS, SHOTS = (os.path.join(ROOT, d) for d in ("evidence", "logs", "screenshots"))
OUT = os.path.join(ROOT, "report", "Assignment1_Report.pdf")
TOPIC = ((STUDENT_ID % 10) - 1) % 5 + 1
TODAY = datetime.date.today().strftime("%d %B %Y")


def safe(t):
    return t.encode("cp1252", "replace").decode("cp1252")


def read(path, default=""):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return default


# ------------------------------------------------------------------ styles
ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13.2, spaceAfter=5)
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=15, textColor=colors.HexColor("#1F3A6E"), spaceBefore=10, spaceAfter=6)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, textColor=colors.HexColor("#1F3A6E"), spaceBefore=8, spaceAfter=4)
CAP = ParagraphStyle("cap", parent=BODY, fontName="Helvetica-Oblique", fontSize=8.3, textColor=colors.HexColor("#444444"), alignment=1)
TITLE = ParagraphStyle("title", parent=H1, fontSize=24, leading=29, alignment=1, spaceAfter=10)
SUB = ParagraphStyle("sub", parent=BODY, fontSize=12, alignment=1, leading=16)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.4, leading=10.4, spaceAfter=0)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)
W = A4[0] - 40 * mm  # usable width


def P(t, st=BODY):
    return Paragraph(t, st)


def bullets(items):
    return [Paragraph("&bull; " + i, ParagraphStyle("b", parent=BODY, leftIndent=10, firstLineIndent=-8, spaceAfter=2)) for i in items]


def table(rows, widths, header=True, font=8.4):
    data = [[Paragraph(safe(str(c)), CELLB if (header and r == 0) else CELL) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A6E")))
    for r in range(1, len(rows)):
        if r % 2 == 0:
            st.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#EEF2F8")))
    t.setStyle(TableStyle(st))
    return t


def code(text, size=5.6, width=158):
    """Monospace block (real terminal output / source). Long lines are wrapped."""
    lines = []
    for ln in safe(text).expandtabs(4).splitlines() or [""]:
        lines.extend(textwrap.wrap(ln, width, subsequent_indent="    ", drop_whitespace=False) or [""])
    st = ParagraphStyle("code", fontName="Courier", fontSize=size, leading=size + 1.4, backColor=colors.HexColor("#F4F4F4"),
                        borderColor=colors.HexColor("#BBBBBB"), borderWidth=0.4, borderPadding=3, spaceAfter=7)
    # split long blocks so they can flow across pages
    out = []
    for i in range(0, len(lines), 70):
        out.append(Preformatted("\n".join(lines[i:i + 70]), st))
    return out


def img(path, width=W, caption=None):
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w, h = im.size
    width = min(width, W)
    height = width * h / w
    if height > 235 * mm:
        height = 235 * mm
        width = height * w / h
    items = [Image(path, width=width, height=height)]
    if caption:
        items.append(P(caption, CAP))
    return KeepTogether(items)


# ------------------------------------------------------------------ figures
def lifecycle_png(path):
    fig, ax = plt.subplots(figsize=(7, 6.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 12); ax.axis("off")
    nodes = {
        "CREATED": (5, 11, "#EAF0FB"), "EXEC_OK": (3, 9, "#EAF0FB"), "EXEC_FAIL": (8.3, 8.2, "#F4CCCC"),
        "RUNNING / SLEEPING": (3, 7, "#EAF0FB"), "TIMEOUT\nSIGTERM to group": (1.6, 5, "#FCE5CD"),
        "KILL\nSIGKILL": (0.9, 3, "#F4CCCC"), "ZOMBIE\n(not yet reaped)": (5.3, 2.3, "#E8E8E8"),
        "EXITED\nWIFEXITED": (3.8, 0.4, "#D9EAD3"), "SIGNALED\nWIFSIGNALED": (7.0, 0.4, "#FFF2CC"),
    }
    for k, (x, y, c) in nodes.items():
        ax.add_patch(FancyBboxPatch((x - 1.15, y - 0.45), 2.3, 0.9, boxstyle="round,pad=0.05", fc=c, ec="black", lw=0.8))
        ax.text(x, y, k, ha="center", va="center", fontsize=7)

    def arrow(a, b, label="", rad=0.0, dx=0, dy=0):
        (x1, y1, _), (x2, y2, _) = nodes[a], nodes[b]
        ax.annotate("", xy=(x2, y2 + (0.5 if y2 < y1 else -0.5)), xytext=(x1, y1 + (-0.5 if y2 < y1 else 0.5)),
                    arrowprops=dict(arrowstyle="->", connectionstyle=f"arc3,rad={rad}", lw=0.9))
        if label:
            ax.text((x1 + x2) / 2 + dx, (y1 + y2) / 2 + dy, label, fontsize=6, ha="center")
    ax.annotate("", xy=(5, 11.5), xytext=(5, 12), arrowprops=dict(arrowstyle="->", lw=0.9))
    ax.text(5.4, 11.8, "fork()", fontsize=6)
    arrow("CREATED", "EXEC_OK", "execvp() ok", dx=-0.9)
    arrow("CREATED", "EXEC_FAIL", "execvp() fails,\nerrno via pipe", dx=1.5, dy=0.3)
    arrow("EXEC_OK", "RUNNING / SLEEPING")
    arrow("RUNNING / SLEEPING", "TIMEOUT\nSIGTERM to group", "run > limit", dx=-1.0)
    arrow("TIMEOUT\nSIGTERM to group", "KILL\nSIGKILL", "grace expired", dx=-0.9)
    arrow("RUNNING / SLEEPING", "ZOMBIE\n(not yet reaped)", "exit() / fatal signal", rad=-0.15, dx=2.2)
    arrow("TIMEOUT\nSIGTERM to group", "ZOMBIE\n(not yet reaped)", "dies", rad=0.1, dx=1.0, dy=-0.5)
    arrow("KILL\nSIGKILL", "ZOMBIE\n(not yet reaped)", rad=0.1)
    arrow("EXEC_FAIL", "ZOMBIE\n(not yet reaped)", "_exit(127)", rad=-0.2, dx=1.8)
    arrow("ZOMBIE\n(not yet reaped)", "EXITED\nWIFEXITED", "waitpid()", dx=-0.8)
    arrow("ZOMBIE\n(not yet reaped)", "SIGNALED\nWIFSIGNALED", "waitpid()", dx=0.9)
    fig.savefig(path, dpi=170, bbox_inches="tight"); plt.close(fig)


def hierarchy_png(path):
    """Process tree drawn from the REAL ps output captured in evidence/ps.txt."""
    rows = {}
    block = read(os.path.join(EV, "ps.txt")).split("$ ps -eo")[-1]
    for ln in block.splitlines():
        f = ln.split(None, 4)
        if len(f) == 5 and f[0].isdigit() and f[1].isdigit() and f[2].isdigit():
            rows[int(f[0])] = (int(f[1]), int(f[2]), f[3], f[4])
    if not rows:
        return False
    sup = next((p for p, v in rows.items() if "procmon" in v[3]), None)
    if sup is None:
        return False
    kids = {p: sorted(c for c, v in rows.items() if v[0] == p) for p in rows}
    levels = {0: [sup]}
    for lvl in (1, 2):
        levels[lvl] = [c for p in levels[lvl - 1] for c in kids.get(p, [])]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
    pos = {}
    ys = {0: 8.4, 1: 5.0, 2: 1.6}
    ax.text(5, 9.7, f"shell  (PID {rows[sup][0]})", ha="center", fontsize=7,
            bbox=dict(boxstyle="round", fc="#F2F2F2", ec="black", lw=0.7))
    for lvl, ps_ in levels.items():
        n = len(ps_)
        for i, p in enumerate(ps_):
            pos[p] = (10 * (i + 0.5) / max(n, 1), ys[lvl])
    cols = {0: "#FCE0CC", 1: "#D6E4F5", 2: "#DCEBD3"}
    for lvl, ps_ in levels.items():
        for p in ps_:
            x, y = pos[p]
            name = os.path.basename(rows[p][3].split()[0]) + " " + " ".join(rows[p][3].split()[1:3]) if lvl else "procmon (supervisor)"
            ax.text(x, y, f"{name}\nPID {p}  PPID {rows[p][0]}\nPGID {rows[p][1]}  STAT {rows[p][2]}", ha="center", va="center",
                    fontsize=6, bbox=dict(boxstyle="round,pad=0.35", fc=cols[lvl], ec="black", lw=0.7))
    ax.annotate("", xy=(pos[sup][0], ys[0] + 0.9), xytext=(5, 9.4), arrowprops=dict(arrowstyle="->", lw=0.8))
    for p in rows:
        for c in kids.get(p, []):
            if c in pos and p in pos:
                ax.annotate("", xy=(pos[c][0], pos[c][1] + 0.95), xytext=(pos[p][0], pos[p][1] - 0.95),
                            arrowprops=dict(arrowstyle="->", lw=0.8))
    # dashed boxes around processes that share one process group (not the supervisor's)
    groups = {}
    for p, v in rows.items():
        if p in pos and p != sup:
            groups.setdefault(v[1], []).append(p)
    for g, mem in groups.items():
        if len(mem) > 1:
            xs = [pos[m][0] for m in mem]; ysx = [pos[m][1] for m in mem]
            ax.add_patch(Rectangle((min(xs) - 1.6, min(ysx) - 1.1), max(xs) - min(xs) + 3.2, max(ysx) - min(ysx) + 2.2,
                                   fill=False, ls="--", ec="#555555", lw=0.8))
            ax.text(min(xs) - 1.5, max(ysx) + 1.2, f"process group {g}", fontsize=5.5)
    fig.savefig(path, dpi=170, bbox_inches="tight"); plt.close(fig)
    return True


def scaling(path):
    """Returns (table_rows, analysis_dict) and saves the graph; all from the real CSV."""
    p = os.path.join(EV, "scaling.csv")
    if not os.path.exists(p):
        return None, None
    data = {}
    with open(p) as f:
        for r in csv.DictReader(f):
            data.setdefault((r["workload"], int(r["n"]), r["mode"]), []).append(float(r["seconds"]))
    ns = sorted({k[1] for k in data})
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.2))
    rows = [["Workload", "Children", "Sequential (s)", "Concurrent (s)", "Speed-up"]]
    best = {}
    for ax, kind, title in zip(axes, ("work", "sleep"), ("CPU-bound children (fixed work each)", "Sleeping children (1 s each)")):
        for mode, colr in (("sequential", "#C0504D"), ("concurrent", "#4F81BD")):
            mean = [statistics.mean(data[(kind, n, mode)]) for n in ns]
            sd = [statistics.pstdev(data[(kind, n, mode)]) for n in ns]
            ax.errorbar(ns, mean, yerr=sd, marker="o", capsize=3, color=colr, label=mode)
        ax.set_title(title, fontsize=8); ax.set_xlabel("number of child processes", fontsize=7)
        ax.set_ylabel("wall-clock time (s)", fontsize=7); ax.set_xticks(ns); ax.grid(alpha=0.3); ax.legend(fontsize=7)
        for n in ns:
            s = statistics.mean(data[(kind, n, "sequential")]); c = statistics.mean(data[(kind, n, "concurrent")])
            rows.append(["CPU-bound" if kind == "work" else "Sleeping", n, f"{s:.3f}", f"{c:.3f}", f"{s / c:.2f}x"])
            best[(kind, n)] = s / c
    fig.tight_layout(); fig.savefig(path, dpi=170); plt.close(fig)
    return rows, best


def env_rows():
    rows = [["Item", "Value"]]
    for ln in read(os.path.join(EV, "env.txt")).splitlines():
        if "|" in ln:
            rows.append(ln.split("|", 1))
    return rows


def ncores():
    for r in env_rows():
        if r[0] == "CPU cores available":
            try:
                return int(r[1].strip())
            except ValueError:
                pass
    return None


# ------------------------------------------------------------------ page decoration
def deco(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5); canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(20 * mm, A4[1] - 12 * mm, f"CSE - Operating Systems | Assignment 1: Process Management        {safe(NAME)} | ID {STUDENT_ID}")
    canvas.line(20 * mm, A4[1] - 13.5 * mm, A4[0] - 20 * mm, A4[1] - 13.5 * mm)
    canvas.drawCentredString(A4[0] / 2, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


# ------------------------------------------------------------------ document
def build():
    os.makedirs(os.path.join(ROOT, "report", "assets"), exist_ok=True)
    A = os.path.join(ROOT, "report", "assets")
    lifecycle_png(os.path.join(A, "lifecycle.png"))
    has_tree = hierarchy_png(os.path.join(A, "hierarchy.png"))
    srows, sbest = scaling(os.path.join(A, "scaling.png"))
    cores = ncores()
    S = []   # story
    fig_no = [0]

    def fig(path, caption, width=W):
        fig_no[0] += 1
        S.append(img(path, width, f"Figure {fig_no[0]}: {caption}"))

    def output(title, fname, size=5.6):
        txt = read(os.path.join(EV, fname))
        S.append(P(f"<b>{title}</b> (real terminal output, file evidence/{fname})", BODY))
        S.extend(code(txt if txt else "(file missing - run ./scripts/run_all.sh first)", size))

    # ---------------- cover
    S += [Spacer(1, 30 * mm), P("OPERATING SYSTEMS", ParagraphStyle("k", parent=SUB, textColor=colors.HexColor("#555555"))),
          P("Assignment 1 - Technical Report", TITLE), P("Process Management and Command Execution in Linux", SUB),
          P("Topic 1: Processes, process states, process creation and termination", SUB), Spacer(1, 6 * mm),
          P("<b>procmon</b> - a fork / exec / waitpid process supervisor with timeout", SUB), Spacer(1, 12 * mm)]
    S.append(table([
        ["Submitted by", NAME], ["Student ID", str(STUDENT_ID)],
        ["Topic number", f"A = (({STUDENT_ID} mod 10) - 1) mod 5 + 1 = {TOPIC}"],
        ["Language / API", "C (C11), POSIX system calls"],
        ["Environment", "; ".join(f"{r[0]}: {r[1]}" for r in env_rows()[1:3]) or "see Table 2"],
        ["GitHub repository", GITHUB_URL], ["Date of submission", TODAY]], [45 * mm, W - 45 * mm], header=False))
    S += [Spacer(1, 10 * mm), P("<b>Contents</b>"),
          *bullets(["1 Introduction and problem statement", "2 Operating-system concepts", "3 Design of the program",
                    "4 Implementation and environment", "5 Test suite", "6 Experimental investigation",
                    "7 Challenge: timeout mechanism", "8 Reflection: limitation and improvement", "9 Conclusion",
                    "Appendix A: source code", "Appendix B: README"]), PageBreak()]

    # ---------------- 1
    S += [P("1. Introduction and problem statement", H1),
          P(f"The assignment topic is selected with A = ((ID mod 10) - 1) mod 5 + 1. For ID {STUDENT_ID}: {STUDENT_ID} mod 10 = {STUDENT_ID % 10}, "
            f"so A = {TOPIC}. Topic 1 asks for a Linux process-monitoring program that shows how an operating system creates, executes, supervises "
            "and terminates processes, and how a parent process relates to its children."),
          P("I wrote <b>procmon</b>, a small supervisor in C. It takes a list of commands, starts each one in its own child process with fork() and "
            "execvp(), watches them with waitpid(), reports how each one ended, and writes a timestamped lifecycle log. A second program, "
            "<b>workload</b>, provides controllable child behaviour (CPU work, sleeping, exit codes, crashes, self-signals, creating grandchildren "
            "and ignoring SIGTERM) so every case can be reproduced on demand."),
          P("<b>Table 1: Mapping of assignment tasks to the implementation</b>"),
          table([["#", "Task", "Where / how"],
                 ["1", "Create child processes with POSIX calls", "fork() in spawn() (real processes, not simulated)"],
                 ["2", "Execute an external program in the child", "execvp() replaces the child image"],
                 ["3", "Parent waits and collects exit status", "waitpid() + WIFEXITED / WEXITSTATUS"],
                 ["4", "Handle failed exec and abnormal termination", "close-on-exec error pipe, WIFSIGNALED / WTERMSIG"],
                 ["5", "Process identification (PID / PPID)", "every log line has pid and ppid; children print getpid() / getppid()"],
                 ["6", "Timestamps and lifecycle log", "millisecond timestamps, 12 event types, log file + stdout"],
                 ["7", "Normal vs signal termination", "Experiment 4 (Section 6.4)"],
                 ["*", "Challenge: timeout", "SIGTERM, grace period, then SIGKILL to the child's process group"]],
                [8 * mm, 62 * mm, W - 70 * mm])]

    # ---------------- 2
    S += [P("2. Operating-system concepts", H1), P("2.1 Process and process states", H2),
          P("A process is a program in execution: an address space (code, data, heap, stack), registers, open files and kernel bookkeeping held "
            "in the process control block (in Linux, task_struct). During its life a process moves between the states new, ready, running, waiting "
            "(blocked) and terminated. Linux shows these in the STAT column of ps: R running or runnable, S interruptible sleep, D uninterruptible "
            "sleep, T stopped and Z zombie."),
          P("2.2 Process creation: fork() and exec()", H2),
          P("fork() creates a near-identical copy of the calling process. It returns twice: 0 in the child and the child's PID in the parent "
            "(-1 on failure). Linux uses copy-on-write, so pages are only duplicated when one side writes to them. The exec family replaces the "
            "current program image with a new one; the PID, PPID, process group and open file descriptors (unless marked close-on-exec) are kept. "
            "Separating creation (fork) from program loading (exec) lets the child set up its environment, here a new process group, in between."),
          P("2.3 Termination, exit status and zombies", H2),
          P("A process ends normally by returning from main or calling exit() / _exit(), or abnormally when a signal whose default action is to "
            "terminate is delivered (SIGSEGV, SIGABRT, SIGKILL, SIGTERM, SIGINT ...). The kernel then keeps a small zombie entry holding the exit "
            "status until the parent collects it with wait() / waitpid(). The status word is decoded with WIFEXITED / WEXITSTATUS for normal exit "
            "and WIFSIGNALED / WTERMSIG / WCOREDUMP for signal death. A parent that never waits leaves zombies behind; if the parent dies first, "
            "the children are re-parented to init (PID 1) or a subreaper."),
          P("2.4 Signals and process groups", H2),
          P("Signals are asynchronous notifications. SIGTERM (15) asks a process to stop and can be caught or ignored; SIGKILL (9) cannot be "
            "caught, blocked or ignored. A process group is a set of related processes that can be signalled together: kill(-pgid, sig) delivers "
            "the signal to every member. procmon puts every child into its own group so it can stop a child together with any grandchildren, "
            "without being able to reach any unrelated process on the system.")]

    # ---------------- 3
    S += [P("3. Design of the program", H1)]
    fig(os.path.join(A, "lifecycle.png"), "Lifecycle of a supervised child as tracked by procmon (log event names in capitals)", 120 * mm)
    S += [P("3.1 Overall structure", H2),
          P("procmon keeps a table of child_t records (PID, command, start / end time, state, exit code or signal, timeout flags). Main steps:"),
          *bullets(["<b>spawn()</b>: creates an error-reporting pipe, records a monotonic start time, calls fork(). The child calls setpgid(0,0), "
                    "restores default signal handlers, splits the command string into argv and calls execvp().",
                    "<b>supervise()</b>: loops over all running children calling waitpid(pid, &amp;status, WNOHANG) every 20 ms. A non-blocking wait "
                    "lets one parent watch many children and enforce timeouts at the same time.",
                    "<b>record_exit()</b>: decodes the status word and writes the EXITED, SIGNALED or REAPED event.",
                    "<b>check_timeout()</b>: implements the challenge (Section 7) and also the SIGKILL escalation after Ctrl+C.",
                    "<b>log_event()</b>: writes one line per event to the log file and to the terminal."]),
          P("3.2 Detecting exec() failure reliably", H2),
          P("After a failed execvp() the child still exists, so the parent cannot tell from fork() alone. Using exit code 127 as the only signal is "
            "ambiguous because a real program may also exit with 127. procmon therefore creates a pipe with O_CLOEXEC before forking. If exec "
            "succeeds, the kernel closes the write end automatically and the parent's read() returns 0 (EOF). If exec fails, the child writes its "
            "errno into the pipe before _exit(127), and the parent logs the exact reason. _exit() is used instead of exit() so that the child does "
            "not flush the parent's copied stdio buffers a second time."),
          P("3.3 Lifecycle log format", H2),
          code("<YYYY-MM-DD HH:MM:SS.mmm> | <EVENT> | pid=<pid> ppid=<ppid> | <details>", 7)[0],
          P("Events: START CREATED EXEC_OK EXEC_FAIL FORK_FAIL EXITED SIGNALED REAPED TIMEOUT KILL INTERRUPT FINISH. Wall-clock time "
            "(CLOCK_REALTIME) is used for the printed timestamp and CLOCK_MONOTONIC for durations, so measured run times cannot be affected by "
            "changes to the system clock."),
          P("3.4 Error handling and safety", H2),
          *bullets(["Every system call result is checked: pipe2, fork (FORK_FAIL event), read (retried on EINTR), waitpid, kill (ESRCH ignored because the child may already be dead).",
                    "Invalid options, negative time values and more than 64 children are rejected with a message. An empty command string reaches the child and is reported as EXEC_FAIL (Invalid argument).",
                    "Ctrl+C on procmon forwards SIGTERM only to its own children's groups, escalates to SIGKILL after the grace period, and still reaps them (test T13).",
                    "procmon only signals PIDs it obtained from its own fork() calls, using their process groups, and only while the child is not yet reaped (a zombie keeps its PID reserved), so it never signals unrelated processes.",
                    "The exit status of procmon is 0 only if every child exited normally with code 0, so it can be used in scripts."])]

    # ---------------- 4
    S += [P("4. Implementation and environment", H1),
          P("The project was developed in Visual Studio Code on Ubuntu and built with GCC through a Makefile using -Wall -Wextra -O2 -std=c11."),
          P("<b>Table 2: Hardware and software environment used for all experiments</b> (collected by scripts/run_all.sh)"),
          table(env_rows(), [45 * mm, W - 45 * mm])]
    S.append(Spacer(1, 3 * mm))
    output("Build output", "build.txt", 6.5)
    shots = sorted(glob.glob(os.path.join(SHOTS, "*.png")) + glob.glob(os.path.join(SHOTS, "*.jpg")))
    if shots:
        S.append(P("<b>Screenshots</b> (taken on my own machine)"))
        for sp in shots:
            fig(sp, os.path.splitext(os.path.basename(sp))[0].replace("_", " ").replace("-", " "), 150 * mm)
    else:
        S.append(P("<i>(No screenshots found in screenshots/ - add your own PNG files and rebuild.)</i>"))

    # ---------------- 5
    S += [P("5. Test suite", H1),
          P("The script tests/run_tests.sh (make test) runs procmon in 14 situations and checks the lifecycle log for the expected event."),
          P("<b>Table 3: Test cases</b>"),
          table([["ID", "Type", "Scenario", "Expected result"],
                 ["T1", "Normal", "workload exit 0", "EXITED, code 0"], ["T2", "Normal", "workload exit 42", "exit status 42 collected"],
                 ["T3", "Failure", "non-existent program", "EXEC_FAIL: No such file or directory"],
                 ["T4", "Failure", "NULL dereference", "SIGNALED, signal 11"], ["T5", "Failure", "abort()", "SIGNALED, signal 6"],
                 ["T6", "Challenge", "sleep 10 with -t 1", "SIGTERM after timeout"],
                 ["T7", "Challenge", "child ignores SIGTERM", "escalated to SIGKILL (9)"],
                 ["T8", "Boundary", "sleep 1 with -t 2", "not killed, exits 0"],
                 ["T9", "Boundary", "empty command string", "rejected (EXEC_FAIL)"],
                 ["T10", "Identity", "two children", "child PPID = supervisor PID"],
                 ["T11", "Cleanup", "mixed exits and crash", "all 3 children reaped"],
                 ["T12", "Failure", "invalid option -x", "usage message, non-zero exit"],
                 ["T13", "Failure", "Ctrl+C while a child ignores SIGTERM", "INTERRUPT, then KILL; procmon exits (no hang)"],
                 ["T14", "Cleanup", "child exits while another still runs", "no zombie (state Z) while procmon is running"]],
                [12 * mm, 22 * mm, 60 * mm, W - 94 * mm])]
    S.append(Spacer(1, 3 * mm))
    output("Test run", "tests.txt", 7)

    # ---------------- 6
    S += [P("6. Experimental investigation", H1),
          P("All experiments are run by scripts/run_experiments.sh and scripts/scaling.sh. The output below is the real terminal output of my run; PIDs and timings differ from run to run."),
          P("6.1 Experiment 1: mixed workload", H2),
          P("Six children are started at once: a CPU-bound child, a sleeping child, a child that exits with code 3, a program that does not exist, a segmentation fault and an abort.")]
    output("Experiment 1", "exp1.txt")
    S += [P("<b>Observations.</b> Each CREATED line is followed by the child's own [workload] line, which prints the same PID after exec: execvp() "
            "replaces the program but keeps the process identity. Every child's PPID equals the supervisor's PID, and the supervisor's PPID is the "
            "shell that started it. The missing program is detected through the error pipe (EXEC_FAIL) and reaped with code 127. The two crashes "
            "are reported as signal 11 and signal 6. Reaping follows the order in which children finish, not the order in which they were created, "
            "and the interleaving of parent and child lines changes from run to run because the scheduler decides which process runs first after fork()."),
          P("6.2 Experiment 2: process hierarchy with ps and pstree", H2),
          P("procmon starts a child that forks three grandchildren, a CPU-bound child and a sleeping child. While they run, ps and pstree are executed from the same session.")]
    output("ps output", "ps.txt")
    output("pstree output", "pstree.txt")
    if has_tree:
        fig(os.path.join(A, "hierarchy.png"), "Process hierarchy diagram drawn from the ps output above", 150 * mm)
    S += [P("<b>Relation to program output.</b> The PPID column shows the tree directly: the supervisor's children have PPID = supervisor PID, and the "
            "grandchildren have PPID = PID of the tree child. The PGID column shows that each child is the leader of its own process group and that "
            "the grandchildren inherited that group; this is why a timeout signal sent to -pgid reaches them too. The STAT column shows the process "
            "states: the busy-loop child is R (running) while the supervisor and the sleeping processes are S (sleeping) because they wait in "
            "nanosleep() or wait(). The grandchildren show the same command line as their parent because they were created by fork() without exec()."),
          P("6.3 Experiment 3: timeout", H2), P("Shown in Section 7 together with the design of the timeout mechanism."),
          P("6.4 Experiment 4: normal termination vs termination by a signal", H2)]
    output("Experiment 4", "exp4.txt")
    S += [P("<b>Table 4: Comparison of normal and signal-based termination</b>"),
          table([["Aspect", "Normal termination", "Termination by a signal"],
                 ["How it happens", "return from main, exit(), _exit()", "signal delivered (kill, raise, CPU fault, timeout)"],
                 ["Who decides", "the process itself", "the kernel or another process"],
                 ["Macro that is true", "WIFEXITED(status)", "WIFSIGNALED(status)"],
                 ["Value collected", "WEXITSTATUS: 0-255 (here 0 and 1)", "WTERMSIG: signal number (here 15, 9, 2, 11)"],
                 ["Clean-up in the process", "exit() and return: atexit handlers run, stdio buffers flushed (_exit() skips both)",
                  "none for SIGKILL; handlers only if the signal is caught"],
                 ["Can be prevented", "n/a", "SIGTERM / SIGINT can be caught or ignored, SIGKILL cannot"],
                 ["Shell exit code", "the exit value", "128 + signal number (e.g. 139 for SIGSEGV)"]],
                [38 * mm, 62 * mm, W - 100 * mm]),
          Spacer(1, 2 * mm),
          P("In both cases the child becomes a zombie and must be reaped by waitpid(); the only difference is how the 16-bit status word is encoded. "
            "A non-zero exit code (code 1) is still a normal termination: the program reported failure, but it was not killed."),
          P("6.5 Experiment 5: concurrent vs sequential supervision and workload size", H2)]
    if srows:
        S += [P("procmon was run with 1, 2, 4 and 8 children, each either CPU-bound (fixed work of 2000 million loop iterations) or sleeping for 1 s. "
                "Each configuration was run three times in concurrent mode and in sequential mode (-s). The graph shows the mean with standard deviation.")]
        fig(os.path.join(A, "scaling.png"), "Wall-clock time vs number of children (mean of 3 runs, error bars = standard deviation)")
        S += [P("<b>Table 5: Timing results (mean of three runs)</b>"), table(srows, [32 * mm, 25 * mm, 38 * mm, 38 * mm, W - 133 * mm])]
        sl8, cpu_best = sbest[("sleep", 8)], max(v for (k, _), v in sbest.items() if k == "work")
        S += [Spacer(1, 2 * mm),
              P(f"<b>Analysis.</b> Sleeping children use almost no CPU, so concurrently they all wait at the same time: the speed-up for 8 sleeping children "
                f"is {sl8:.2f}x, while the sequential time grows linearly with the number of children. CPU-bound children compete for the processor: "
                f"the best CPU-bound speed-up measured is {cpu_best:.2f}x"
                + (f" on a machine with {cores} CPU core(s) available, and it cannot exceed the number of cores that can run in parallel" if cores else "")
                + ". Beyond that point the scheduler only time-shares the runnable processes over the available cores. Creating a process is cheap "
                "(a full fork + exec + wait cycle for a trivial child takes a few milliseconds, see Experiment 4), so the limit is the number of CPU "
                "cores, not the cost of process creation. Run-to-run noise is why three repetitions were used.")]
    else:
        S.append(P("<i>(evidence/scaling.csv missing - run ./scripts/run_all.sh)</i>"))

    # ---------------- 7
    S += [P("7. Challenge: timeout mechanism", H1),
          P("The supervisor accepts -t seconds (execution limit) and -g seconds (grace period). Because supervise() already polls each child with WNOHANG, "
            "the timeout check is done in the same loop and needs no extra thread or timer signal:"),
          *bullets(["When a child's monotonic run time exceeds the limit, procmon logs TIMEOUT and sends <b>SIGTERM</b> to the child's process group, kill(-pid, SIGTERM). This gives the program a chance to clean up.",
                    "If the child is still alive after the grace period, it logs KILL and sends <b>SIGKILL</b>, which cannot be ignored.",
                    "Using the process group also stops any grandchildren, which would otherwise be left running as orphans.",
                    "The child is still reaped normally by waitpid(), and its record is marked [TIMEOUT]."]),
          P("Experiment 3 starts four children with limit 2 s and grace 1 s: a 1-second sleeper (finishes normally), a 10-second CPU loop, a program that "
            "ignores SIGTERM (hang), and a tree child with grandchildren.")]
    output("Experiment 3", "exp3.txt")
    S += [P("<b>Result.</b> The child that finishes before the limit is not affected. The CPU-bound child and the tree child (with its grandchildren) "
            "are terminated by SIGTERM shortly after the limit. The hang child ignores SIGTERM, so it survives the first signal and is killed by SIGKILL "
            "after the grace period. The 20 ms polling interval explains why the times are slightly above the limits.")]

    # ---------------- 8, 9
    S += [P("8. Reflection: limitation and improvement", H1),
          P("<b>Limitation.</b> Supervision uses polling: the parent wakes up every 20 ms even when nothing happens. This costs a little CPU time and limits "
            "timeout accuracy to about 20 ms. In addition, commands are split only on spaces, so quoted arguments, pipes and redirection are not supported."),
          P("<b>Improvement.</b> Polling could be replaced with an event-driven design: on Linux, pidfd_open() returns a file descriptor for each child that "
            "becomes readable when the child exits, and poll() can wait on all of them with a timeout equal to the nearest deadline. The parent would then "
            "sleep until something actually happens, timeouts would be exact, and PID reuse races would be avoided. A second improvement would be to "
            "record resource usage per child with wait4() (CPU time, maximum memory)."),
          P("9. Conclusion", H1),
          P("procmon shows the full life of a process on Linux: creation with fork(), program loading with execvp(), the running and sleeping states visible "
            "in ps, termination either normally or by a signal, and reaping by the parent with waitpid() so no zombies remain. The tests and experiments "
            "show that the PID / PPID relations in the log match the hierarchy shown by pstree, that exec failures and crashes are reported correctly, and "
            "that the timeout stops runaway children, including ones that ignore SIGTERM, without affecting any unrelated process."),
          P("References", H2),
          *bullets(["A. Silberschatz, P. B. Galvin, G. Gagne, Operating System Concepts, 10th ed., Wiley, 2018, ch. 3.",
                    "Linux manual pages: fork(2), execve(2), exec(3), waitpid(2), kill(2), setpgid(2), pipe(2), signal(7), ps(1), pstree(1).",
                    "M. Kerrisk, The Linux Programming Interface, No Starch Press, 2010, ch. 24-28."]),
          PageBreak()]

    # ---------------- appendices
    S.append(P("Appendix A. Source code", H1))
    for rel in ("src/procmon.c", "src/workload.c", "Makefile", "tests/run_tests.sh", "scripts/run_experiments.sh",
                "scripts/scaling.sh", "scripts/run_all.sh"):
        S.append(P(f"A. {rel}", H2))
        S.extend(code(read(os.path.join(ROOT, rel)), 5.8, 150))
    S += [PageBreak(), P("Appendix B. README and build instructions", H1)]
    S.extend(code(read(os.path.join(ROOT, "README.md")), 6.3, 125))
    S.append(P("Lifecycle log of Experiment 3 (logs/exp3.log)", H2))
    S.extend(code(read(os.path.join(LOGS, "exp3.log")), 5.6))

    SimpleDocTemplate(OUT, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=17 * mm,
                      title=f"OS Assignment 1 - procmon - {NAME}", author=NAME).build(S, onFirstPage=lambda c, d: None, onLaterPages=deco)
    print("written:", OUT)


if __name__ == "__main__":
    build()
