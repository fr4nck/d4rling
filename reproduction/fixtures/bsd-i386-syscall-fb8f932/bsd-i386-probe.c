/*
 * D4rling BSD i386 probe (lot B15-XNU, 14 Nov 2026).
 * Real Mach-O i386 guest witness for the BSD syscall return conventions of
 * darling-xnu fb8f932: direct stubs (SYS.h -errno -> CF conversion), the
 * 64-bit lseek stub, syscall(2), unknown syscall numbers (table bound and
 * .no_sys), the machdep LDT wrappers and per-thread errno.
 *
 * Output: one "BSDP <section> <name> PASS|FAIL <detail>" line per check,
 * then "BSDP_SUMMARY checks=N failures=M section_failures=A:B:C:D:E:F".
 * Exit status: 0 if every check passed, 10 otherwise.
 * Risky calls (unknown numbers, >= table size) run in a forked child so a
 * crash is recorded as a failure instead of killing the probe.
 */
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/attr.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/vnode.h>
#include <unistd.h>

int syscall(int, ...);
int i386_get_ldt(int start_sel, void *descs, int num_sels);
int i386_set_ldt(int start_sel, const void *descs, int num_sels);

static unsigned checks, failures;
static unsigned sec_fail[6];
static const char *sec_names = "ABCDEF";

static void check(int section, const char *name, int ok, const char *fmt, ...)
	__attribute__((format(printf, 4, 5)));

#include <stdarg.h>
static void check(int section, const char *name, int ok, const char *fmt, ...)
{
	char detail[256];
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(detail, sizeof detail, fmt, ap);
	va_end(ap);
	++checks;
	if (!ok) {
		++failures;
		++sec_fail[section];
	}
	printf("BSDP %c %s %s %s\n", sec_names[section], name, ok ? "PASS" : "FAIL", detail);
	fflush(stdout);
}

enum { A = 0, B, C, D, E, F };

/* ---------- B/C: raw syscall() in a child, with captured output ---------- */
struct child_result {
	int ret;
	int err;
};

/* Runs syscall(nr) (no meaningful args) in a child; nr -6 / -5 run
 * i386_get_ldt / i386_set_ldt (machdep traps 6 / 5) instead. Returns 0 if the child
 * exited normally and fills res/msg; otherwise returns the signal number. */
static int run_child_syscall(int nr, struct child_result *res, char *msg, size_t msglen, int *exited_code)
{
	int out[2], rp[2];
	if (pipe(out) || pipe(rp))
		return -1;
	fflush(stdout);
	pid_t pid = fork();
	if (pid < 0)
		return -1;
	if (pid == 0) {
		close(out[0]);
		close(rp[0]);
		dup2(out[1], 1);
		dup2(out[1], 2);
		signal(SIGSYS, SIG_IGN);
		struct child_result r;
		errno = 0;
		static unsigned char ldt_buf[16];
		if (nr == -6)
			r.ret = i386_get_ldt(0, ldt_buf, 1);
		else if (nr == -5)
			r.ret = i386_set_ldt(0, ldt_buf, 0);
		else
			r.ret = syscall(nr, 0, 0, 0, 0, 0, 0);
		r.err = errno;
		write(rp[1], &r, sizeof r);
		_exit(0);
	}
	close(out[1]);
	close(rp[1]);
	size_t used = 0;
	ssize_t n;
	while (used + 1 < msglen && (n = read(out[0], msg + used, msglen - 1 - used)) > 0)
		used += (size_t)n;
	msg[used] = 0;
	for (char *p = msg; *p; ++p)
		if (*p == '\n' || *p == ' ')
			*p = '_';
	memset(res, 0, sizeof *res);
	ssize_t got = read(rp[0], res, sizeof *res);
	close(out[0]);
	close(rp[0]);
	int status = 0;
	waitpid(pid, &status, 0);
	*exited_code = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
	if (WIFSIGNALED(status))
		return WTERMSIG(status);
	if (got != (ssize_t)sizeof *res)
		return -2;
	return 0;
}

static void unknown_syscall_case(int section, const char *name, int nr)
{
	struct child_result r;
	char msg[256];
	int code = -1;
	int sig = run_child_syscall(nr, &r, msg, sizeof msg, &code);
	if (sig != 0) {
		check(section, name, 0, "nr=%d child_signal_or_error=%d exit=%d out=%s", nr, sig, code, msg);
		return;
	}
	check(section, name, r.ret == -1 && r.err == ENOSYS,
	      "nr=%d ret=%d errno=%d out=%s", nr, r.ret, r.err, msg);
	/* .no_sys must report the requested (masked) number, not an address. */
	char want[64];
	snprintf(want, sizeof want, "Unimplemented_syscall_(%d)", nr & 0xffff);
	char lname[96];
	snprintf(lname, sizeof lname, "%s_reported_number", name);
	check(section, lname, strstr(msg, want) != NULL, "want=%s out=%s", want, msg);
}

/* ---------- E: per-thread errno under concurrency ---------- */
static const char *g_neg;
static volatile int g_go;
struct thr {
	int id;
	unsigned stub_bad, sys_bad, calls;
};

static void *worker(void *arg)
{
	struct thr *t = arg;
	while (!g_go)
		;
	for (unsigned i = 0; i < 200; ++i) {
		int r;
		switch ((i + (unsigned)t->id) % 4) {
		case 0:
			errno = 0;
			r = access(g_neg, F_OK);
			if (r != -1 || errno != ENOENT) ++t->stub_bad;
			break;
		case 1:
			errno = 0;
			r = close(-1);
			if (r != -1 || errno != EBADF) ++t->stub_bad;
			break;
		case 2:
			errno = 0;
			if (lseek(-1, 0, SEEK_SET) != (off_t)-1 || errno != EBADF) ++t->stub_bad;
			break;
		case 3:
			errno = 0;
			r = syscall(SYS_access, g_neg, F_OK);
			if (r != -1 || errno != ENOENT) ++t->sys_bad;
			break;
		}
		++t->calls;
	}
	return NULL;
}

int main(void)
{
	char pos[128], neg[128];
	snprintf(pos, sizeof pos, "/tmp/BSDP_POS_%d", (int)getpid());
	snprintf(neg, sizeof neg, "/tmp/BSDP_NEG_%d", (int)getpid());
	g_neg = neg;
	printf("BSDP_STARTED pointer=%u off_t=%u\n", (unsigned)sizeof(void *), (unsigned)sizeof(off_t));

	int fd = open(pos, O_CREAT | O_EXCL | O_RDWR, 0600);
	check(A, "open_create", fd >= 0, "fd=%d errno=%d", fd, errno);
	struct stat st;
	char resolved[1024];

	/* A: ordinary stubs, SYS.h -errno -> CF conversion */
	errno = 0; int r = access(pos, F_OK);
	check(A, "access_ok", r == 0, "ret=%d errno=%d", r, errno);
	errno = 0; r = access(neg, F_OK);
	check(A, "access_ENOENT", r == -1 && errno == ENOENT, "ret=%d errno=%d", r, errno);
	errno = 0; r = stat(pos, &st);
	check(A, "stat64_ok", r == 0 && S_ISREG(st.st_mode), "ret=%d errno=%d mode=%o", r, errno, (unsigned)st.st_mode);
	errno = 0; r = stat(neg, &st);
	check(A, "stat64_ENOENT", r == -1 && errno == ENOENT, "ret=%d errno=%d", r, errno);
	errno = 0; r = lstat(pos, &st);
	check(A, "lstat64_ok", r == 0, "ret=%d errno=%d", r, errno);
	errno = 0; r = lstat(neg, &st);
	check(A, "lstat64_ENOENT", r == -1 && errno == ENOENT, "ret=%d errno=%d", r, errno);
	/* /tmp may resolve through /private/tmp: compare the objects, not the strings.
	 * errno is unspecified after a successful realpath(), so it is only reported. */
	struct stat st_pos, st_res;
	errno = 0; char *rp = realpath(pos, resolved);
	int rp_errno = errno;
	int same = rp != NULL && resolved[0] == '/' && stat(pos, &st_pos) == 0 && stat(resolved, &st_res) == 0 &&
	           st_pos.st_dev == st_res.st_dev && st_pos.st_ino == st_res.st_ino;
	check(A, "realpath_ok", same, "ret=%s errno=%d", rp ? resolved : "NULL", rp_errno);
	errno = 0; rp = realpath(neg, resolved);
	check(A, "realpath_ENOENT", rp == NULL && errno == ENOENT, "ret=%s errno=%d", rp ? "nonNULL" : "NULL", errno);

	struct attrlist al;
	struct { uint32_t length; fsobj_type_t type; } __attribute__((packed)) ab;
	memset(&al, 0, sizeof al);
	al.bitmapcount = ATTR_BIT_MAP_COUNT;
	al.commonattr = ATTR_CMN_OBJTYPE;
	memset(&ab, 0, sizeof ab);
	errno = 0; r = getattrlist(pos, &al, &ab, sizeof ab, 0);
	check(A, "getattrlist_ok", r == 0 && ab.type == VREG, "ret=%d errno=%d len=%u type=%u", r, errno, ab.length, (unsigned)ab.type);
	errno = 0; r = getattrlist(neg, &al, &ab, sizeof ab, 0);
	check(A, "getattrlist_ENOENT", r == -1 && errno == ENOENT, "ret=%d errno=%d", r, errno);
	al.bitmapcount = 0;
	errno = 0; r = getattrlist(pos, &al, &ab, sizeof ab, 0);
	check(A, "getattrlist_EINVAL", r == -1 && errno == EINVAL, "ret=%d errno=%d", r, errno);

	/* B: 64-bit lseek, low word inside the -4095..-1 range */
	static const long long offs[] = { 0x1fffffffeLL, 0x2fffff001LL, 0x3fffff000LL, 0x7fffffffLL, 0x80000000LL };
	for (unsigned i = 0; fd >= 0 && i < sizeof offs / sizeof offs[0]; ++i) {
		char name[48];
		snprintf(name, sizeof name, "lseek64_set_%llx", offs[i]);
		errno = 0; off_t o = lseek(fd, (off_t)offs[i], SEEK_SET);
		check(B, name, o == (off_t)offs[i], "ret=%lld errno=%d", (long long)o, errno);
		snprintf(name, sizeof name, "lseek64_cur_%llx", offs[i]);
		errno = 0; o = lseek(fd, 0, SEEK_CUR);
		check(B, name, o == (off_t)offs[i], "ret=%lld errno=%d", (long long)o, errno);
	}
	errno = 0; off_t lo = fd >= 0 ? lseek(fd, -1, SEEK_SET) : 0;
	check(B, "lseek_EINVAL", lo == (off_t)-1 && errno == EINVAL, "ret=%lld errno=%d", (long long)lo, errno);
	errno = 0; lo = lseek(-1, 0, SEEK_SET);
	check(B, "lseek_EBADF", lo == (off_t)-1 && errno == EBADF, "ret=%lld errno=%d", (long long)lo, errno);

	/* C: syscall(2) relay through ___syscall */
	errno = 0; r = syscall(SYS_getpid);
	check(C, "syscall_getpid", r == (int)getpid(), "ret=%d pid=%d errno=%d", r, (int)getpid(), errno);
	errno = 0; r = syscall(SYS_access, pos, F_OK);
	check(C, "syscall_access_ok", r == 0, "ret=%d errno=%d", r, errno);
	errno = 0; r = syscall(SYS_access, neg, F_OK);
	check(C, "syscall_access_ENOENT", r == -1 && errno == ENOENT, "ret=%d errno=%d", r, errno);
	errno = 0; r = syscall(SYS_close, -1);
	check(C, "syscall_close_EBADF", r == -1 && errno == EBADF, "ret=%d errno=%d", r, errno);

	/* D: unknown numbers: empty slots below the table size, then >= 600 */
	unknown_syscall_case(D, "unknown_8", 8);
	unknown_syscall_case(D, "unknown_599", 599);
	unknown_syscall_case(D, "unknown_600", 600);
	unknown_syscall_case(D, "unknown_1000", 1000);
	unknown_syscall_case(D, "unknown_65535", 65535);

	/* E: machdep LDT wrappers (traps 5/6 are not implemented by Darling):
	 * -1 with errno set, and the unknown-trap report names the trap. */
	for (int trap = 6; trap >= 5; --trap) {
		struct child_result cr;
		char msg[256], name[64], want[64];
		int code = -1;
		int sig = run_child_syscall(-trap, &cr, msg, sizeof msg, &code);
		snprintf(name, sizeof name, "%s_error", trap == 6 ? "i386_get_ldt" : "i386_set_ldt");
		if (sig != 0) {
			check(E, name, 0, "child_signal_or_error=%d exit=%d out=%s", sig, code, msg);
			continue;
		}
		check(E, name, cr.ret == -1 && cr.err == ENOSYS, "ret=%d errno=%d", cr.ret, cr.err);
		snprintf(name, sizeof name, "%s_reported_trap", trap == 6 ? "i386_get_ldt" : "i386_set_ldt");
		snprintf(want, sizeof want, "Unimplemented_machdep_trap_(%d)", trap);
		check(E, name, strstr(msg, want) != NULL, "want=%s out=%s", want, msg);
	}

	/* F: per-thread errno under concurrency (stubs and syscall(2) kept apart) */
	pthread_t th[4];
	struct thr ts[4];
	int created = 0;
	for (int i = 0; i < 4; ++i) {
		memset(&ts[i], 0, sizeof ts[i]);
		ts[i].id = i;
		if (pthread_create(&th[i], NULL, worker, &ts[i]) == 0)
			++created;
	}
	g_go = 1;
	unsigned stub_bad = 0, sys_bad = 0, calls = 0;
	for (int i = 0; i < created; ++i) {
		pthread_join(th[i], NULL);
		stub_bad += ts[i].stub_bad;
		sys_bad += ts[i].sys_bad;
		calls += ts[i].calls;
	}
	check(F, "threads_created", created == 4, "created=%d", created);
	check(F, "threads_calls", calls == 800, "calls=%u", calls);
	check(F, "threads_errno_stubs", stub_bad == 0, "bad=%u of 600", stub_bad);
	check(F, "threads_errno_syscall", sys_bad == 0, "bad=%u of 200", sys_bad);

	if (fd >= 0) {
		close(fd);
		unlink(pos);
	}
	printf("BSDP_SUMMARY checks=%u failures=%u section_failures=A%u:B%u:C%u:D%u:E%u:F%u\n",
	       checks, failures, sec_fail[A], sec_fail[B], sec_fail[C], sec_fail[D], sec_fail[E], sec_fail[F]);
	puts(failures ? "BSDP_FINISHED_WITH_FAILURES" : "BSDP_FINISHED_OK");
	return failures ? 10 : 0;
}
