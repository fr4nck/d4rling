/* X2 side check: x86_64 syscall(2) with numbers outside the 600-entry table.
 * syscall(2) on x86_64 enters the dispatcher with the constant SYS_syscall (0);
 * the number is checked in C by sys_syscall(). Each call runs in a child. */
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
int syscall(int, ...);
int main(void)
{
	static const int nrs[] = {0, 8, 599, 600, 1000, 65535, 65536, 0x7fffffff, -1};
	int bad = 0;
	setvbuf(stdout, NULL, _IONBF, 0);
	for (unsigned i = 0; i < sizeof nrs / sizeof nrs[0]; ++i) {
		int p[2], o[2];
		pipe(p); pipe(o);
		pid_t pid = fork();
		if (pid == 0) {
			dup2(o[1], 2);
			errno = 0;
			int r = syscall(nrs[i], 0, 0, 0, 0, 0, 0);
			int e = errno, v[2] = {r, e};
			write(p[1], v, sizeof v);
			_exit(0);
		}
		close(p[1]); close(o[1]);
		int v[2] = {0, 0};
		char msg[160] = "";
		ssize_t g = read(p[0], v, sizeof v);
		ssize_t m = read(o[0], msg, sizeof msg - 1);
		if (m > 0) msg[m] = 0;
		for (char *q = msg; *q; ++q) if (*q == '\n' || *q == ' ') *q = '_';
		int st = 0;
		waitpid(pid, &st, 0);
		int ok = g == (ssize_t)sizeof v && WIFEXITED(st) && v[0] == -1 && v[1] == ENOSYS;
		bad += !ok;
		printf("X64 nr=%d %s ret=%d errno=%d signal=%d out=%s\n", nrs[i], ok ? "PASS" : "FAIL", v[0], v[1],
		       WIFSIGNALED(st) ? WTERMSIG(st) : 0, msg);
		close(p[0]); close(o[0]);
	}
	printf("X64_SUMMARY failures=%d\n", bad);
	return bad ? 10 : 0;
}
