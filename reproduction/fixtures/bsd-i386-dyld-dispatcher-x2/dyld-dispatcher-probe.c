/*
 * D4rling lot X2 (14 Nov 2026): direct witness for the BSD i386 dispatcher
 * built into dyld (__darling_bsd_syscall, static copy of the darling-xnu
 * emulation linked into the loader), as opposed to the one in
 * libsystem_kernel.dylib.
 *
 * Every dyld address used here is resolved at run time from the dyld image
 * that is actually mapped in this process (dyld_all_image_infos ->
 * dyldImageLoadAddress, then dyld's own LC_SYMTAB in its mapped __LINKEDIT).
 * The probe checks that the mapped __TEXT and the dispatcher bytes are
 * identical to the dyld file it hashes from inside the guest, and that the
 * libsystem_kernel dispatcher is a different function.
 *
 * Attribution: in a forked child, the first byte of the dyld dispatcher's
 * entry NOP sled (the xtrace hook, 7 x 0x90) is replaced by int3 in the
 * child's private copy of the page. Each entry raises SIGTRAP; the handler
 * records the entry address, %eax (requested number) and the return
 * address, then resumes on the remaining NOPs. A call counts as "through the
 * dyld dispatcher" only if such an entry was recorded.
 *
 * Sections:
 *  I identity: mapped dyld == hashed dyld file, symbols owned by dyld,
 *    libsystem_kernel dispatcher distinct.
 *  P dyld's own path: dlopen() makes dyld's internal stubs enter its
 *    dispatcher; libSystem syscall() does not.
 *  S dyld's syscall(2) stub (_syscall inside dyld) -> dyld dispatcher:
 *    valid calls, errors, unknown numbers 8/599/600/1000/65535.
 *  D direct call of the dyld dispatcher with a stub-shaped frame: raw
 *    result (-errno), reported number, preserved registers.
 *  G table-read guard: the dyld page holding &__bsd_syscall_table[nr] is
 *    made PROT_NONE in the child before a direct call; nr 599 is the
 *    positive control (must fault on exactly that entry).
 *  W dyld's own BSD wrappers (_stat64, _lstat64, _access,
 *    _getattrlist$UNIX2003, 64-bit _lseek) called at their dyld address:
 *    success, ENOENT/EINVAL/EBADF, lseek offsets whose low word lies in
 *    -4095..-1; each entering the dyld dispatcher from that wrapper.
 *
 * Output: "X2 <section> <name> PASS|FAIL <detail>" and "X2_INFO ..." lines,
 * then "X2_SUMMARY checks=N failures=M section_failures=I..:P..:S..:D..:G..:W..".
 * Exit status 0 if every check passed, 10 otherwise.
 */
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/attr.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/ucontext.h>
#include <sys/vnode.h>
#include <sys/wait.h>
#include <unistd.h>
#include <mach/mach.h>
#include <mach-o/dyld.h>
#include <mach-o/dyld_images.h>
#include <mach-o/fat.h>
#include <mach-o/loader.h>
#include <mach-o/nlist.h>

int syscall(int, ...);

/* ------------------------------------------------------------------ report */
static unsigned checks, failures;
static unsigned sec_fail[6];
static const char sec_names[] = "IPSDGW";
enum { SI = 0, SP, SS, SD, SG, SW };

static void check(int sec, const char *name, int ok, const char *fmt, ...)
	__attribute__((format(printf, 4, 5)));
static void check(int sec, const char *name, int ok, const char *fmt, ...)
{
	char detail[512];
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(detail, sizeof detail, fmt, ap);
	va_end(ap);
	++checks;
	if (!ok) {
		++failures;
		++sec_fail[sec];
	}
	printf("X2 %c %s %s %s\n", sec_names[sec], name, ok ? "PASS" : "FAIL", detail);
	fflush(stdout);
}

/* ------------------------------------------------------------------ sha256 */
typedef struct { uint32_t h[8]; uint64_t len; uint8_t buf[64]; size_t n; } sha256_t;
static const uint32_t K256[64] = {
	0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
	0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
	0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
	0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
	0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
	0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
	0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
	0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
#define ROR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))
static void sha_block(sha256_t *s, const uint8_t *p)
{
	uint32_t w[64], a, b, c, d, e, f, g, h;
	for (int i = 0; i < 16; ++i)
		w[i] = (uint32_t)p[4 * i] << 24 | (uint32_t)p[4 * i + 1] << 16 | (uint32_t)p[4 * i + 2] << 8 | p[4 * i + 3];
	for (int i = 16; i < 64; ++i) {
		uint32_t s0 = ROR(w[i - 15], 7) ^ ROR(w[i - 15], 18) ^ (w[i - 15] >> 3);
		uint32_t s1 = ROR(w[i - 2], 17) ^ ROR(w[i - 2], 19) ^ (w[i - 2] >> 10);
		w[i] = w[i - 16] + s0 + w[i - 7] + s1;
	}
	a = s->h[0]; b = s->h[1]; c = s->h[2]; d = s->h[3]; e = s->h[4]; f = s->h[5]; g = s->h[6]; h = s->h[7];
	for (int i = 0; i < 64; ++i) {
		uint32_t t1 = h + (ROR(e, 6) ^ ROR(e, 11) ^ ROR(e, 25)) + ((e & f) ^ (~e & g)) + K256[i] + w[i];
		uint32_t t2 = (ROR(a, 2) ^ ROR(a, 13) ^ ROR(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
		h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
	}
	s->h[0] += a; s->h[1] += b; s->h[2] += c; s->h[3] += d; s->h[4] += e; s->h[5] += f; s->h[6] += g; s->h[7] += h;
}
static void sha_init(sha256_t *s)
{
	static const uint32_t iv[8] = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
	memcpy(s->h, iv, sizeof iv);
	s->len = 0;
	s->n = 0;
}
static void sha_update(sha256_t *s, const void *data, size_t len)
{
	const uint8_t *p = data;
	s->len += len;
	while (len) {
		size_t k = 64 - s->n < len ? 64 - s->n : len;
		memcpy(s->buf + s->n, p, k);
		s->n += k; p += k; len -= k;
		if (s->n == 64) {
			sha_block(s, s->buf);
			s->n = 0;
		}
	}
}
static void sha_hex(sha256_t *s, char out[65])
{
	uint64_t bits = s->len * 8;
	uint8_t pad = 0x80, z = 0, l[8];
	sha_update(s, &pad, 1);
	while (s->n != 56)
		sha_update(s, &z, 1);
	for (int i = 0; i < 8; ++i)
		l[i] = (uint8_t)(bits >> (56 - 8 * i));
	sha_update(s, l, 8);
	for (int i = 0; i < 8; ++i)
		snprintf(out + 8 * i, 9, "%08x", s->h[i]);
}
static void sha_mem(const void *p, size_t n, char out[65])
{
	sha256_t s;
	sha_init(&s);
	sha_update(&s, p, n);
	sha_hex(&s, out);
}

/* ------------------------------------------------------------------ images */
struct image {
	const char *label;
	uintptr_t mh;
	intptr_t slide;
	uint32_t lo, hi;            /* slid range of all non-empty segments */
	uint32_t text_lo, text_hi;  /* slid __TEXT */
	uint32_t text_vmaddr, text_fileoff, text_filesize;
	const struct nlist *syms;
	uint32_t nsyms;
	const char *strs;
	uint32_t strsize;
	uint8_t uuid[16];
	int have_uuid;
};

static int parse_image(struct image *im, const char *label, const struct mach_header *mh, intptr_t slide)
{
	memset(im, 0, sizeof *im);
	im->label = label;
	im->mh = (uintptr_t)mh;
	im->slide = slide;
	im->lo = 0xffffffffu;
	if (mh->magic != MH_MAGIC)
		return -1;
	const struct load_command *lc = (const void *)(mh + 1);
	const struct segment_command *linkedit = NULL;
	const struct symtab_command *st = NULL;
	for (uint32_t i = 0; i < mh->ncmds; ++i, lc = (const void *)((const char *)lc + lc->cmdsize)) {
		if (lc->cmd == LC_SEGMENT) {
			const struct segment_command *sc = (const void *)lc;
			if (sc->vmsize && strcmp(sc->segname, "__PAGEZERO")) {
				uint32_t a = sc->vmaddr + (uint32_t)slide;
				if (a < im->lo) im->lo = a;
				if (a + sc->vmsize > im->hi) im->hi = a + sc->vmsize;
			}
			if (!strcmp(sc->segname, "__TEXT")) {
				im->text_lo = sc->vmaddr + (uint32_t)slide;
				im->text_hi = im->text_lo + sc->vmsize;
				im->text_vmaddr = sc->vmaddr;
				im->text_fileoff = sc->fileoff;
				im->text_filesize = sc->filesize;
			}
			if (!strcmp(sc->segname, "__LINKEDIT"))
				linkedit = sc;
		} else if (lc->cmd == LC_SYMTAB) {
			st = (const void *)lc;
		} else if (lc->cmd == LC_UUID) {
			memcpy(im->uuid, ((const struct uuid_command *)lc)->uuid, 16);
			im->have_uuid = 1;
		}
	}
	if (!linkedit || !st)
		return -2;
	uintptr_t le = linkedit->vmaddr + (uint32_t)slide - linkedit->fileoff;
	im->syms = (const void *)(le + st->symoff);
	im->nsyms = st->nsyms;
	im->strs = (const char *)(le + st->stroff);
	im->strsize = st->strsize;
	return 0;
}

/* Finds a defined N_SECT symbol by exact name. Returns its slid address or 0;
 * *type receives n_type, *next the slid address of the following symbol in
 * the same section (function end). */
static uint32_t find_sym(const struct image *im, const char *name, uint8_t *type, uint32_t *next)
{
	const struct nlist *hit = NULL;
	for (uint32_t i = 0; i < im->nsyms; ++i) {
		const struct nlist *n = &im->syms[i];
		if ((n->n_type & N_STAB) || (n->n_type & N_TYPE) != N_SECT)
			continue;
		if (n->n_un.n_strx >= im->strsize)
			continue;
		if (!strcmp(im->strs + n->n_un.n_strx, name)) {
			hit = n;
			break;
		}
	}
	if (!hit)
		return 0;
	if (type)
		*type = hit->n_type;
	if (next) {
		uint32_t best = 0xffffffffu;
		for (uint32_t i = 0; i < im->nsyms; ++i) {
			const struct nlist *n = &im->syms[i];
			if ((n->n_type & N_STAB) || (n->n_type & N_TYPE) != N_SECT || n->n_sect != hit->n_sect)
				continue;
			if (n->n_value > hit->n_value && n->n_value < best)
				best = n->n_value;
		}
		*next = best == 0xffffffffu ? 0 : best + (uint32_t)im->slide;
	}
	return hit->n_value + (uint32_t)im->slide;
}

/* Nearest preceding N_SECT symbol for a slid address. */
static const char *sym_for(const struct image *im, uint32_t addr, uint32_t *off)
{
	const struct nlist *best = NULL;
	uint32_t v = addr - (uint32_t)im->slide;
	for (uint32_t i = 0; i < im->nsyms; ++i) {
		const struct nlist *n = &im->syms[i];
		if ((n->n_type & N_STAB) || (n->n_type & N_TYPE) != N_SECT || n->n_un.n_strx >= im->strsize)
			continue;
		if (n->n_value <= v && (!best || n->n_value > best->n_value))
			best = n;
	}
	if (!best)
		return "?";
	*off = v - best->n_value;
	return im->strs + best->n_un.n_strx;
}

static int in_range(uint32_t a, uint32_t lo, uint32_t hi) { return a >= lo && a < hi; }

static struct image dy, ks;          /* dyld, libsystem_kernel */
static uint32_t d_disp, d_disp_end, d_sys, d_unk, d_tbl;
static uint32_t probe_lo, probe_hi;  /* this executable */

/* ------------------------------------------------------------------ file */
static uint8_t *read_file(const char *path, size_t *len)
{
	int fd = open(path, O_RDONLY);
	if (fd < 0)
		return NULL;
	struct stat sb;
	if (fstat(fd, &sb)) {
		close(fd);
		return NULL;
	}
	uint8_t *p = malloc((size_t)sb.st_size);
	size_t got = 0;
	while (p && got < (size_t)sb.st_size) {
		ssize_t r = read(fd, p + got, (size_t)sb.st_size - got);
		if (r <= 0)
			break;
		got += (size_t)r;
	}
	close(fd);
	if (!p || got != (size_t)sb.st_size) {
		free(p);
		return NULL;
	}
	*len = got;
	return p;
}

/* i386 slice of a fat or thin Mach-O file. */
static const uint8_t *i386_slice(const uint8_t *f, size_t len, size_t *slen)
{
	if (len < 8)
		return NULL;
	uint32_t magic = (uint32_t)f[0] << 24 | (uint32_t)f[1] << 16 | (uint32_t)f[2] << 8 | f[3];
	if (magic == FAT_MAGIC) {
		uint32_t n = (uint32_t)f[4] << 24 | (uint32_t)f[5] << 16 | (uint32_t)f[6] << 8 | f[7];
		for (uint32_t i = 0; i < n && 8 + 20 * (i + 1) <= len; ++i) {
			const uint8_t *a = f + 8 + 20 * i;
			uint32_t cpu = (uint32_t)a[0] << 24 | (uint32_t)a[1] << 16 | (uint32_t)a[2] << 8 | a[3];
			uint32_t off = (uint32_t)a[8] << 24 | (uint32_t)a[9] << 16 | (uint32_t)a[10] << 8 | a[11];
			uint32_t sz = (uint32_t)a[12] << 24 | (uint32_t)a[13] << 16 | (uint32_t)a[14] << 8 | a[15];
			if (cpu == CPU_TYPE_I386 && (size_t)off + sz <= len) {
				*slen = sz;
				return f + off;
			}
		}
		return NULL;
	}
	if (((const struct mach_header *)f)->magic == MH_MAGIC && ((const struct mach_header *)f)->cputype == CPU_TYPE_I386) {
		*slen = len;
		return f;
	}
	return NULL;
}

/* ------------------------------------------------------------------ trap */
#define MAXHITS 24
struct cres {
	int ret, err, expect;
	uint32_t regs[7];           /* eax ecx edx ebx esi edi ebp after a direct call */
	uint32_t esp_before, esp_after;
	uint32_t hits, n;
	uint32_t eip[MAXHITS], eax[MAXHITS], rat[MAXHITS];
	int faulted, fault_sig;
	uint32_t fault_addr, fault_eip;
	int armed;                  /* 1 if int3 was written, -1 on failure */
	int aux;
	long long ret64;
	uint8_t buf[256];           /* K_W32 output buffer (struct stat64, attributes) */
};
static struct cres *g_res;
static int g_resfd = -1;

static void trap_handler(int sig, siginfo_t *si, void *ctx)
{
	(void)sig; (void)si;
	ucontext_t *uc = ctx;
	uint32_t eip = uc->uc_mcontext->__ss.__eip;
	uint32_t eax = uc->uc_mcontext->__ss.__eax;
	uint32_t esp = uc->uc_mcontext->__ss.__esp;
	if (g_res->n < MAXHITS) {
		g_res->eip[g_res->n] = eip;
		g_res->eax[g_res->n] = eax;
		g_res->rat[g_res->n] = *(volatile uint32_t *)(uintptr_t)esp;
		g_res->n++;
	}
	g_res->hits++;
}

static void fault_handler(int sig, siginfo_t *si, void *ctx)
{
	ucontext_t *uc = ctx;
	g_res->faulted = 1;
	g_res->fault_sig = sig;
	g_res->fault_addr = (uint32_t)(uintptr_t)si->si_addr;
	g_res->fault_eip = uc->uc_mcontext->__ss.__eip;
	write(g_resfd, g_res, sizeof *g_res);
	_exit(77);
}

static int arm(void)
{
	uintptr_t page = d_disp & ~(uintptr_t)4095;
	if (mprotect((void *)page, 4096, PROT_READ | PROT_WRITE | PROT_EXEC))
		return -1;
	volatile uint8_t *p = (volatile uint8_t *)(uintptr_t)d_disp;
	if (*p != 0x90)
		return -2;
	*p = 0xcc;
	return 1;
}
static void disarm(void)
{
	*(volatile uint8_t *)(uintptr_t)d_disp = 0x90;
	mprotect((void *)(d_disp & ~(uintptr_t)4095), 4096, PROT_READ | PROT_EXEC);
}

/* Direct call of a dispatcher with the frame an i386 stub gives it:
 * [esp] return into the caller, [esp+4] the caller's own return address,
 * [esp+8...] arguments; %eax = number. Sentinels in the other registers. */
struct dcall {
	uint32_t fn, nr, a[6];          /* 0, 4, 8..28 */
	uint32_t out[7];                /* 32..56: eax ecx edx ebx esi edi ebp */
	uint32_t esp_before, esp_after; /* 60, 64 */
};
void x2_dcall(struct dcall *c);
extern char x2_dcall_ret[];
__asm__(
	".text\n"
	".globl _x2_dcall\n"
	".globl _x2_dcall_ret\n"
	"_x2_dcall:\n"
	"	pushl %ebp\n	pushl %ebx\n	pushl %esi\n	pushl %edi\n"
	"	movl 20(%esp), %eax\n"
	"	pushl %eax\n"
	"	pushl 28(%eax)\n	pushl 24(%eax)\n	pushl 20(%eax)\n"
	"	pushl 16(%eax)\n	pushl 12(%eax)\n	pushl 8(%eax)\n"
	"	pushl $0\n"
	"	movl %esp, 60(%eax)\n"
	"	movl 0(%eax), %edx\n"
	"	movl 4(%eax), %eax\n"
	"	movl $0x5ec5ec5e, %ecx\n	movl $0x0b0b0b0b, %ebx\n	movl $0x51515151, %esi\n"
	"	movl $0xd1d1d1d1, %edi\n	movl $0xebebebeb, %ebp\n"
	"	calll *%edx\n"
	"_x2_dcall_ret:\n"
	"	pushl %ebp\n	pushl %edi\n	pushl %esi\n	pushl %ebx\n	pushl %edx\n	pushl %ecx\n	pushl %eax\n"
	"	movl 56(%esp), %ebx\n"
	"	popl %eax\n	movl %eax, 32(%ebx)\n	popl %eax\n	movl %eax, 36(%ebx)\n"
	"	popl %eax\n	movl %eax, 40(%ebx)\n	popl %eax\n	movl %eax, 44(%ebx)\n"
	"	popl %eax\n	movl %eax, 48(%ebx)\n	popl %eax\n	movl %eax, 52(%ebx)\n"
	"	popl %eax\n	movl %eax, 56(%ebx)\n"
	"	movl %esp, 64(%ebx)\n"
	"	addl $28, %esp\n	popl %eax\n"
	"	popl %edi\n	popl %esi\n	popl %ebx\n	popl %ebp\n"
	"	ret\n");

/* ------------------------------------------------------------------ child */
enum kind { K_STUB, K_DIRECT, K_GUARD, K_DLOPEN, K_LIBSYS, K_W32, K_LSEEK };
struct job {
	enum kind kind;
	int nr;
	uint32_t a[6];
	const char *path;  /* K_DLOPEN */
	int trap;
	uint32_t fn;       /* K_W32 / K_LSEEK: dyld wrapper address */
	long long off;     /* K_LSEEK */
	int bufarg;        /* K_W32: index of the argument replaced by r->buf, or -1 */
};

static void child_body(const struct job *j, struct cres *r)
{
	struct sigaction sa;
	memset(&sa, 0, sizeof sa);
	sa.sa_sigaction = fault_handler;
	sa.sa_flags = SA_SIGINFO;
	sigaction(SIGSEGV, &sa, NULL);
	sigaction(SIGBUS, &sa, NULL);
	sigaction(SIGILL, &sa, NULL);
	sa.sa_sigaction = trap_handler;
	sigaction(SIGTRAP, &sa, NULL);
	signal(SIGSYS, SIG_IGN);
	r->expect = getpid();
	if (j->trap)
		r->armed = arm();
	if (j->trap && r->armed != 1)
		return;
	switch (j->kind) {
	case K_STUB: {
		int (*f)(int, ...) = (int (*)(int, ...))(uintptr_t)d_sys;
		errno = 0;
		r->ret = f(j->nr, j->a[0], j->a[1], j->a[2], j->a[3], j->a[4], j->a[5]);
		r->err = errno;
		break;
	}
	case K_GUARD: {
		uintptr_t entry = d_tbl + 4u * (uint32_t)(j->nr & 0xffff);
		r->aux = (int)entry;
		if (mprotect((void *)(entry & ~(uintptr_t)4095), 4096, PROT_NONE)) {
			r->aux = -1;
			return;
		}
	}
		/* fall through */
	case K_DIRECT: {
		struct dcall c;
		memset(&c, 0, sizeof c);
		c.fn = d_disp;
		c.nr = (uint32_t)j->nr;
		memcpy(c.a, j->a, sizeof c.a);
		x2_dcall(&c);
		memcpy(r->regs, c.out, sizeof r->regs);
		r->esp_before = c.esp_before;
		r->esp_after = c.esp_after;
		r->ret = (int)c.out[0];
		break;
	}
	case K_DLOPEN: {
		void *h = dlopen(j->path, RTLD_NOW);
		r->ret = h != NULL;
		if (!h) {
			const char *e = dlerror();
			printf("dlerror=%s\n", e ? e : "(null)");
		}
		break;
	}
	case K_W32: {
		int (*f)(uint32_t, uint32_t, uint32_t, uint32_t, uint32_t) =
			(int (*)(uint32_t, uint32_t, uint32_t, uint32_t, uint32_t))(uintptr_t)j->fn;
		uint32_t a[5];
		memcpy(a, j->a, sizeof a);
		if (j->bufarg >= 0)
			a[j->bufarg] = (uint32_t)(uintptr_t)r->buf;
		errno = 0;
		r->ret = f(a[0], a[1], a[2], a[3], a[4]);
		r->err = errno;
		break;
	}
	case K_LSEEK: {
		long long (*f)(int, long long, int) = (long long (*)(int, long long, int))(uintptr_t)j->fn;
		errno = 0;
		r->ret64 = f((int)j->a[0], j->off, (int)j->a[1]);
		r->err = errno;
		break;
	}
	case K_LIBSYS:
		errno = 0;
		r->ret = syscall(j->nr, j->a[0], j->a[1], j->a[2], j->a[3], j->a[4], j->a[5]);
		r->err = errno;
		break;
	}
	if (j->trap)
		disarm();
}

/* Returns 0 if the child completed and *r is filled, 77 if it recorded a fault,
 * or the terminating signal / -1. msg receives its stdout+stderr ('_' for blanks). */
static int run_job(const struct job *j, struct cres *r, char *msg, size_t msglen)
{
	int out[2], rp[2];
	memset(r, 0, sizeof *r);
	if (pipe(out) || pipe(rp))
		return -1;
	fflush(stdout);
	fflush(stderr);
	pid_t pid = fork();
	if (pid < 0)
		return -1;
	if (pid == 0) {
		close(out[0]);
		close(rp[0]);
		dup2(out[1], 1);
		dup2(out[1], 2);
		static struct cres cr;
		memset(&cr, 0, sizeof cr);
		g_res = &cr;
		g_resfd = rp[1];
		child_body(j, &cr);
		fflush(stdout);
		write(rp[1], &cr, sizeof cr);
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
	ssize_t got = read(rp[0], r, sizeof *r);
	close(out[0]);
	close(rp[0]);
	int status = 0;
	waitpid(pid, &status, 0);
	if (WIFSIGNALED(status))
		return WTERMSIG(status);
	if (got != (ssize_t)sizeof *r)
		return -2;
	if (WIFEXITED(status) && WEXITSTATUS(status) == 77 && r->faulted)
		return 77;
	return WIFEXITED(status) && WEXITSTATUS(status) == 0 ? 0 : -3;
}

static void print_hits(const char *tag, const struct cres *r)
{
	for (uint32_t i = 0; i < r->n; ++i) {
		uint32_t off = 0;
		const char *owner = in_range(r->rat[i], dy.text_lo, dy.text_hi) ? "dyld"
		                    : in_range(r->rat[i], probe_lo, probe_hi) ? "probe"
		                    : in_range(r->rat[i], ks.text_lo, ks.text_hi) ? "libsystem_kernel" : "other";
		const char *s = !strcmp(owner, "dyld") ? sym_for(&dy, r->rat[i], &off) : "-";
		/* dyld's internal stubs put flags above bit 15; the dispatcher masks them */
		printf("X2_INFO %s hit=%u entry=0x%08x eax=0x%08x nr=%u caller=0x%08x owner=%s sym=%s+0x%x\n",
		       tag, i, r->eip[i] - 1, r->eax[i], r->eax[i] & 0xffff, r->rat[i], owner, s, off);
	}
}

/* The first trap hit must be the dyld dispatcher entry with %eax == nr. */
static int first_hit_ok(const struct cres *r, int nr, uint32_t want_caller_lo, uint32_t want_caller_hi)
{
	return r->n >= 1 && r->eip[0] == d_disp + 1 && r->eax[0] == (uint32_t)nr &&
	       in_range(r->rat[0], want_caller_lo, want_caller_hi);
}

/* ------------------------------------------------------------------ sections */
static const char *neg_path = "/x2-nonexistent/absent";

static void section_s(int nr, const char *name, uint32_t a0, uint32_t a1, int want_ret, int want_err, int is_unknown)
{
	struct job j = {.kind = K_STUB, .nr = nr, .a = {a0, a1, 0, 0, 0, 0}, .path = NULL, .trap = 1, .bufarg = -1};
	struct cres r;
	char msg[512], cname[96];
	int st = run_job(&j, &r, msg, sizeof msg);
	char tag[64];
	snprintf(tag, sizeof tag, "S_%s", name);
	print_hits(tag, &r);
	snprintf(cname, sizeof cname, "%s_ret", name);
	if (st != 0) {
		check(SS, cname, 0, "nr=%d child_status=%d fault_addr=0x%08x fault_eip=0x%08x armed=%d out=%s",
		      nr, st, r.fault_addr, r.fault_eip, r.armed, msg);
		return;
	}
	if (want_ret == -2) /* getpid */
		want_ret = r.expect;
	check(SS, cname, r.ret == want_ret && (want_ret != -1 || r.err == want_err),
	      "nr=%d ret=%d errno=%d want_ret=%d want_errno=%d", nr, r.ret, r.err, want_ret, want_err);
	snprintf(cname, sizeof cname, "%s_via_dyld_dispatcher", name);
	check(SS, cname, first_hit_ok(&r, nr, d_sys, d_sys + 0x40),
	      "hits=%u first_entry=0x%08x first_nr=%u first_caller=0x%08x dyld_syscall=0x%08x",
	      r.hits, r.n ? r.eip[0] - 1 : 0, r.n ? r.eax[0] : 0, r.n ? r.rat[0] : 0, d_sys);
	if (is_unknown) {
		char want[64];
		snprintf(want, sizeof want, "Unimplemented_syscall_(%d)", nr & 0xffff);
		snprintf(cname, sizeof cname, "%s_reported_number", name);
		check(SS, cname, strstr(msg, want) != NULL, "want=%s out=%s", want, msg);
	}
}

static void section_d(int nr, const char *name, uint32_t a0, uint32_t a1, int want_raw, int is_unknown)
{
	struct job j = {.kind = K_DIRECT, .nr = nr, .a = {a0, a1, 0, 0, 0, 0}, .path = NULL, .trap = 1, .bufarg = -1};
	struct cres r;
	char msg[512], cname[96], tag[64];
	int st = run_job(&j, &r, msg, sizeof msg);
	snprintf(tag, sizeof tag, "D_%s", name);
	print_hits(tag, &r);
	snprintf(cname, sizeof cname, "%s_raw", name);
	if (st != 0) {
		check(SD, cname, 0, "nr=%d child_status=%d fault_addr=0x%08x fault_eip=0x%08x armed=%d out=%s",
		      nr, st, r.fault_addr, r.fault_eip, r.armed, msg);
		return;
	}
	if (want_raw == -2000) /* getpid */
		want_raw = r.expect;
	check(SD, cname, (int)r.regs[0] == want_raw, "nr=%d eax=%d want=%d edx=0x%08x", nr, (int)r.regs[0], want_raw, r.regs[2]);
	snprintf(cname, sizeof cname, "%s_entry", name);
	check(SD, cname, first_hit_ok(&r, nr, (uint32_t)(uintptr_t)x2_dcall_ret, (uint32_t)(uintptr_t)x2_dcall_ret + 1),
	      "hits=%u first_entry=0x%08x dyld_dispatcher=0x%08x first_nr=%u caller=0x%08x",
	      r.hits, r.n ? r.eip[0] - 1 : 0, d_disp, r.n ? r.eax[0] : 0, r.n ? r.rat[0] : 0);
	/* Callee-saved registers and the stack pointer always survive; %ecx must
	 * survive a handled call (Darwin i386 convention kept by the dispatcher). */
	int saved = r.regs[3] == 0x0b0b0b0b && r.regs[4] == 0x51515151 && r.regs[5] == 0xd1d1d1d1 &&
	            r.regs[6] == 0xebebebeb && r.esp_after == r.esp_before;
	int ecx_ok = is_unknown || r.regs[1] == 0x5ec5ec5e;
	snprintf(cname, sizeof cname, "%s_registers", name);
	check(SD, cname, saved && ecx_ok, "ebx=0x%08x esi=0x%08x edi=0x%08x ebp=0x%08x ecx=0x%08x%s esp_before=0x%08x esp_after=0x%08x",
	      r.regs[3], r.regs[4], r.regs[5], r.regs[6], r.regs[1], is_unknown ? "(not_required)" : "",
	      r.esp_before, r.esp_after);
	if (is_unknown) {
		char want[64];
		snprintf(want, sizeof want, "Unimplemented_syscall_(%d)", nr & 0xffff);
		snprintf(cname, sizeof cname, "%s_reported_number", name);
		check(SD, cname, strstr(msg, want) != NULL, "want=%s out=%s", want, msg);
	}
}

static void section_g(int nr, const char *name, int control)
{
	struct job j = {.kind = K_GUARD, .nr = nr, .a = {0, 0, 0, 0, 0, 0}, .path = NULL, .trap = 0, .bufarg = -1};
	struct cres r;
	char msg[512], cname[96];
	uint32_t entry = d_tbl + 4u * (uint32_t)(nr & 0xffff);
	int st = run_job(&j, &r, msg, sizeof msg);
	printf("X2_INFO G_%s nr=%d table=0x%08x entry=0x%08x guarded_page=0x%08x in_dyld=%d status=%d fault_addr=0x%08x fault_eip=0x%08x eax=%d\n",
	       name, nr, d_tbl, entry, entry & ~4095u, in_range(entry, dy.lo, dy.hi), st, r.fault_addr, r.fault_eip,
	       (int)r.regs[0]);
	snprintf(cname, sizeof cname, "%s_%s", name, control ? "control_read_detected" : "no_table_read");
	if (control)
		check(SG, cname, st == 77 && r.fault_addr == entry && in_range(r.fault_eip, d_disp, d_disp_end),
		      "status=%d fault_addr=0x%08x want=0x%08x fault_eip=0x%08x", st, r.fault_addr, entry, r.fault_eip);
	else
		check(SG, cname, st == 0 && (int)r.regs[0] == -ENOSYS && r.aux == (int)entry,
		      "status=%d eax=%d fault_addr=0x%08x fault_eip=0x%08x out=%s", st, (int)r.regs[0], r.fault_addr,
		      r.fault_eip, msg);
}

static int image_loaded(const char *suffix)
{
	size_t sl = strlen(suffix);
	for (uint32_t i = 0; i < _dyld_image_count(); ++i) {
		const char *n = _dyld_get_image_name(i);
		size_t l = n ? strlen(n) : 0;
		if (l >= sl && !strcmp(n + l - sl, suffix))
			return 1;
	}
	return 0;
}

static void section_p(void)
{
	struct cres r;
	char msg[512];
	/* dyld's own loader path, failing lookup */
	struct job j1 = {.kind = K_DLOPEN, .nr = 0, .a = {0}, .path = "/x2-nonexistent/libx2.dylib", .trap = 1, .bufarg = -1};
	int st = run_job(&j1, &r, msg, sizeof msg);
	print_hits("P_dlopen_absent", &r);
	int all_dyld = r.n > 0;
	for (uint32_t i = 0; i < r.n; ++i)
		all_dyld &= r.eip[i] == d_disp + 1 && in_range(r.rat[i], dy.text_lo, dy.text_hi);
	check(SP, "dlopen_absent_enters_dyld_dispatcher", st == 0 && r.ret == 0 && r.hits > 0 && all_dyld,
	      "status=%d handle=%d hits=%u all_callers_in_dyld_text=%d out=%s", st, r.ret, r.hits, all_dyld, msg);
	/* dyld's own loader path, real load of an image not yet mapped */
	const char *lib = "/usr/lib/libz.1.dylib";
	int pre = image_loaded("/libz.1.dylib");
	struct job j2 = {.kind = K_DLOPEN, .nr = 0, .a = {0}, .path = lib, .trap = 1, .bufarg = -1};
	st = run_job(&j2, &r, msg, sizeof msg);
	print_hits("P_dlopen_libz", &r);
	all_dyld = r.n > 0;
	for (uint32_t i = 0; i < r.n; ++i)
		all_dyld &= r.eip[i] == d_disp + 1 && in_range(r.rat[i], dy.text_lo, dy.text_hi);
	check(SP, "dlopen_libz_enters_dyld_dispatcher", !pre && st == 0 && r.ret == 1 && r.hits > 0 && all_dyld,
	      "preloaded=%d status=%d handle=%d hits=%u all_callers_in_dyld_text=%d out=%s", pre, st, r.ret, r.hits,
	      all_dyld, msg);
	/* Negative control: libSystem's syscall() uses libsystem_kernel's dispatcher */
	struct job j3 = {.kind = K_LIBSYS, .nr = SYS_getpid, .a = {0}, .path = NULL, .trap = 1, .bufarg = -1};
	st = run_job(&j3, &r, msg, sizeof msg);
	print_hits("P_libsystem_getpid", &r);
	check(SP, "libsystem_syscall_getpid_not_dyld", st == 0 && r.ret == r.expect && r.hits == 0,
	      "status=%d ret=%d pid=%d dyld_hits=%u", st, r.ret, r.expect, r.hits);
	struct job j4 = {.kind = K_LIBSYS, .nr = 65535, .a = {0}, .path = NULL, .trap = 1, .bufarg = -1};
	st = run_job(&j4, &r, msg, sizeof msg);
	print_hits("P_libsystem_65535", &r);
	/* Attribution only: the result belongs to libsystem_kernel (qualified in X1;
	 * before darling-xnu#102 this call crashes there), not to dyld. */
	check(SP, "libsystem_syscall_65535_not_dyld", (st == 0 || st == 77) && r.hits == 0,
	      "status=%d ret=%d errno=%d dyld_hits=%u fault_eip=0x%08x fault_in_libsystem_kernel=%d out=%s", st, r.ret,
	      r.err, r.hits, r.fault_eip, st == 77 && in_range(r.fault_eip, ks.text_lo, ks.text_hi), msg);
}

/* ------------------------------------------------------------------ W */
static int g_wfd = -1;
static const char *g_wpos;
static struct stat g_wst;

/* The first trap hit must be the dyld dispatcher, entered from the wrapper
 * itself with the wrapper's number (dyld's stubs carry flags above bit 15). */
static int wrap_hit_ok(const struct cres *r, uint32_t fn, int nr)
{
	return r->n >= 1 && r->eip[0] == d_disp + 1 && (r->eax[0] & 0xffff) == (uint32_t)nr && in_range(r->rat[0], fn, fn + 0x30);
}

static void w_case(const char *name, const char *sym, int nr, struct job *j, int (*judge)(const struct cres *, char *, size_t))
{
	struct cres r;
	char msg[512] = "", cname[96], tag[64], det[256] = "";
	memset(&r, 0, sizeof r);
	uint32_t fn = find_sym(&dy, sym, NULL, NULL);
	j->fn = fn;
	j->trap = 1;
	int st = fn ? run_job(j, &r, msg, sizeof msg) : -9;
	snprintf(tag, sizeof tag, "W_%s", name);
	print_hits(tag, &r);
	snprintf(cname, sizeof cname, "%s_ret", name);
	int ok = st == 0 && judge(&r, det, sizeof det);
	check(SW, cname, ok, "wrapper=%s@0x%08x status=%d %s out=%s", sym, fn, st, det, msg);
	snprintf(cname, sizeof cname, "%s_via_dyld_dispatcher", name);
	check(SW, cname, st == 0 && wrap_hit_ok(&r, fn, nr), "hits=%u first_entry=0x%08x first_eax=0x%08x want_nr=%d caller=0x%08x",
	      r.hits, r.n ? r.eip[0] - 1 : 0, r.n ? r.eax[0] : 0, nr, r.n ? r.rat[0] : 0);
}

static int j_stat_ok(const struct cres *r, char *d, size_t n)
{
	const struct stat *st = (const void *)r->buf;
	snprintf(d, n, "ret=%d errno=%d ino=%llu/%llu size=%lld", r->ret, r->err, (unsigned long long)st->st_ino,
	         (unsigned long long)g_wst.st_ino, (long long)st->st_size);
	return r->ret == 0 && st->st_ino == g_wst.st_ino && st->st_size == g_wst.st_size && S_ISREG(st->st_mode);
}
static int j_enoent(const struct cres *r, char *d, size_t n)
{
	snprintf(d, n, "ret=%d errno=%d want=-1/ENOENT", r->ret, r->err);
	return r->ret == -1 && r->err == ENOENT;
}
static int j_einval(const struct cres *r, char *d, size_t n)
{
	snprintf(d, n, "ret=%d errno=%d want=-1/EINVAL", r->ret, r->err);
	return r->ret == -1 && r->err == EINVAL;
}
static int j_attr_ok(const struct cres *r, char *d, size_t n)
{
	uint32_t len;
	fsobj_type_t type;
	memcpy(&len, r->buf, 4);
	memcpy(&type, r->buf + 4, sizeof type);
	snprintf(d, n, "ret=%d errno=%d len=%u type=%u", r->ret, r->err, len, (unsigned)type);
	return r->ret == 0 && type == VREG;
}
static long long g_off;
static int j_lseek_off(const struct cres *r, char *d, size_t n)
{
	snprintf(d, n, "ret64=0x%llx want=0x%llx errno=%d", (unsigned long long)r->ret64, (unsigned long long)g_off, r->err);
	return r->ret64 == g_off;
}
static int j_lseek_err(const struct cres *r, char *d, size_t n)
{
	snprintf(d, n, "ret64=%lld errno=%d want=-1/%d", r->ret64, r->err, (int)g_off);
	return r->ret64 == -1 && r->err == (int)g_off;
}

static void section_w(void)
{
	char pos[64];
	snprintf(pos, sizeof pos, "/tmp/X2_W_%d", (int)getpid());
	g_wpos = pos;
	g_wfd = open(pos, O_CREAT | O_RDWR | O_TRUNC, 0644);
	if (g_wfd < 0 || write(g_wfd, "x2", 2) != 2 || fstat(g_wfd, &g_wst)) {
		check(SW, "setup", 0, "path=%s fd=%d errno=%d", pos, g_wfd, errno);
		return;
	}
	uint32_t P = (uint32_t)(uintptr_t)pos, N = (uint32_t)(uintptr_t)neg_path;
	struct job j;
#define JOB(k, a0, a1, a2, a3, a4, ba) \
	(memset(&j, 0, sizeof j), j.kind = (k), j.a[0] = (a0), j.a[1] = (a1), j.a[2] = (a2), j.a[3] = (a3), j.a[4] = (a4), \
	 j.bufarg = (ba), &j)
	w_case("stat64_ok", "_stat64", SYS_stat64, JOB(K_W32, P, 0, 0, 0, 0, 1), j_stat_ok);
	w_case("stat64_enoent", "_stat64", SYS_stat64, JOB(K_W32, N, 0, 0, 0, 0, 1), j_enoent);
	w_case("lstat64_enoent", "_lstat64", SYS_lstat64, JOB(K_W32, N, 0, 0, 0, 0, 1), j_enoent);
	w_case("access_enoent", "_access", SYS_access, JOB(K_W32, N, F_OK, 0, 0, 0, -1), j_enoent);
	static struct attrlist al, al0;
	memset(&al, 0, sizeof al);
	al.bitmapcount = ATTR_BIT_MAP_COUNT;
	al.commonattr = ATTR_CMN_OBJTYPE;
	al0 = al;
	al0.bitmapcount = 0;
	uint32_t AL = (uint32_t)(uintptr_t)&al, AL0 = (uint32_t)(uintptr_t)&al0;
	w_case("getattrlist_ok", "_getattrlist$UNIX2003", SYS_getattrlist, JOB(K_W32, P, AL, 0, 8, 0, 2), j_attr_ok);
	w_case("getattrlist_enoent", "_getattrlist$UNIX2003", SYS_getattrlist, JOB(K_W32, N, AL, 0, 8, 0, 2), j_enoent);
	w_case("getattrlist_einval", "_getattrlist$UNIX2003", SYS_getattrlist, JOB(K_W32, P, AL0, 0, 8, 0, 2), j_einval);
	static const long long offs[] = {0x1fffffffeLL, 0x2fffff001LL, 0x3fffff000LL};
	for (unsigned i = 0; i < sizeof offs / sizeof offs[0]; ++i) {
		char nm[48];
		snprintf(nm, sizeof nm, "lseek_%llx", offs[i]);
		g_off = offs[i];
		JOB(K_LSEEK, (uint32_t)g_wfd, SEEK_SET, 0, 0, 0, -1);
		j.off = offs[i];
		w_case(nm, "_lseek", SYS_lseek, &j, j_lseek_off);
	}
	g_off = EINVAL;
	JOB(K_LSEEK, (uint32_t)g_wfd, SEEK_SET, 0, 0, 0, -1);
	j.off = -1;
	w_case("lseek_einval", "_lseek", SYS_lseek, &j, j_lseek_err);
	g_off = EBADF;
	JOB(K_LSEEK, (uint32_t)-1, SEEK_SET, 0, 0, 0, -1);
	j.off = 0;
	w_case("lseek_ebadf", "_lseek", SYS_lseek, &j, j_lseek_err);
#undef JOB
	close(g_wfd);
	unlink(pos);
}

static int identity(void)
{
	char hex[65];
	sha_mem("abc", 3, hex);
	check(SI, "sha256_selftest", !strcmp(hex, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"), "abc=%s", hex);

	struct task_dyld_info tdi;
	memset(&tdi, 0, sizeof tdi);
	mach_msg_type_number_t cnt = TASK_DYLD_INFO_COUNT;
	kern_return_t kr = task_info(mach_task_self(), TASK_DYLD_INFO, (task_info_t)&tdi, &cnt);
	const struct dyld_all_image_infos *ai =
		kr == KERN_SUCCESS ? (const struct dyld_all_image_infos *)(uintptr_t)tdi.all_image_info_addr : NULL;
	check(SI, "all_image_infos", ai != NULL, "task_info_kr=%d all_image_info_addr=0x%llx", kr,
	      (unsigned long long)tdi.all_image_info_addr);
	if (!ai)
		return -1;
	const struct mach_header *mh = ai->dyldImageLoadAddress;
	const char *dpath = ai->version >= 15 && ai->dyldPath ? ai->dyldPath : "/usr/lib/dyld";
	int ok = mh && mh->magic == MH_MAGIC && mh->cputype == CPU_TYPE_I386 && mh->filetype == MH_DYLINKER;
	check(SI, "dyld_header", ok, "load_address=%p filetype=%u path=%s version=%u", (void *)mh, ok ? mh->filetype : 0,
	      dpath, ai->version);
	if (!ok)
		return -1;
	/* __TEXT of dyld starts at vmaddr 0 in this build; slide from the header */
	struct image tmp;
	parse_image(&tmp, "dyld", mh, 0);
	intptr_t slide = (intptr_t)(uintptr_t)mh - (intptr_t)tmp.text_vmaddr;
	if (parse_image(&dy, "dyld", mh, slide))
		return -1;
	printf("X2_INFO dyld load_address=0x%08x slide=0x%08x text=0x%08x-0x%08x image=0x%08x-0x%08x nsyms=%u path=%s\n",
	       (uint32_t)dy.mh, (uint32_t)slide, dy.text_lo, dy.text_hi, dy.lo, dy.hi, dy.nsyms, dpath);

	uint8_t tdisp = 0, tsys = 0, tunk = 0, ttbl = 0;
	d_disp = find_sym(&dy, "__darling_bsd_syscall", &tdisp, &d_disp_end);
	d_sys = find_sym(&dy, "_syscall", &tsys, NULL);
	d_unk = find_sym(&dy, "___unknown_syscall", &tunk, NULL);
	d_tbl = find_sym(&dy, "___bsd_syscall_table", &ttbl, NULL);
	ok = d_disp && d_sys && d_unk && d_tbl && in_range(d_disp, dy.text_lo, dy.text_hi) &&
	     in_range(d_sys, dy.text_lo, dy.text_hi) && in_range(d_unk, dy.text_lo, dy.text_hi) &&
	     in_range(d_tbl, dy.lo, dy.hi) && !in_range(d_tbl, dy.text_lo, dy.text_hi) && d_disp_end > d_disp;
	check(SI, "dyld_symbols", ok,
	      "dispatcher=0x%08x end=0x%08x syscall=0x%08x unknown=0x%08x table=0x%08x types=%02x/%02x/%02x/%02x",
	      d_disp, d_disp_end, d_sys, d_unk, d_tbl, tdisp, tsys, tunk, ttbl);
	if (!ok)
		return -1;
	/* the all_image_infos structure the kernel side reports is dyld's own */
	uint32_t d_aii = find_sym(&dy, "_dyld_all_image_infos", NULL, NULL);
	check(SI, "all_image_infos_owned_by_dyld", d_aii == (uint32_t)(uintptr_t)ai, "dyld_symbol=0x%08x task_info=0x%08x",
	      d_aii, (uint32_t)(uintptr_t)ai);
	check(SI, "dyld_symbols_private", !(tdisp & N_EXT) && !(tsys & N_EXT) && !(tunk & N_EXT),
	      "dispatcher_ext=%d syscall_ext=%d unknown_ext=%d", !!(tdisp & N_EXT), !!(tsys & N_EXT), !!(tunk & N_EXT));

	/* File identity, from inside the guest */
	size_t flen = 0, slen = 0;
	uint8_t *file = read_file(dpath, &flen);
	const uint8_t *slice = file ? i386_slice(file, flen, &slen) : NULL;
	if (file) {
		sha_mem(file, flen, hex);
		printf("X2_INFO dyld_file path=%s size=%zu sha256=%s\n", dpath, flen, hex);
		printf("X2_DYLD_SHA256 %s\n", hex);
	}
	check(SI, "dyld_file_i386_slice", slice != NULL, "path=%s size=%zu slice_size=%zu", dpath, flen, slen);
	if (!slice)
		return -1;
	struct image fimg;
	int fuuid = 0;
	{
		/* UUID of the file slice */
		const struct mach_header *fmh = (const void *)slice;
		const struct load_command *lc = (const void *)(fmh + 1);
		for (uint32_t i = 0; i < fmh->ncmds; ++i, lc = (const void *)((const char *)lc + lc->cmdsize))
			if (lc->cmd == LC_UUID) {
				memcpy(fimg.uuid, ((const struct uuid_command *)lc)->uuid, 16);
				fuuid = 1;
			}
	}
	char u1[33] = "", u2[33] = "";
	for (int i = 0; i < 16; ++i) {
		snprintf(u1 + 2 * i, 3, "%02x", dy.uuid[i]);
		snprintf(u2 + 2 * i, 3, "%02x", fimg.uuid[i]);
	}
	check(SI, "dyld_uuid_mapped_equals_file", dy.have_uuid && fuuid && !memcmp(dy.uuid, fimg.uuid, 16),
	      "mapped=%s file=%s", u1, u2);
	char hm[65], hf[65];
	int text_ok = dy.text_fileoff + dy.text_filesize <= slen && dy.text_filesize == dy.text_hi - dy.text_lo;
	if (text_ok) {
		sha_mem((const void *)(uintptr_t)dy.text_lo, dy.text_filesize, hm);
		sha_mem(slice + dy.text_fileoff, dy.text_filesize, hf);
	}
	check(SI, "dyld_text_mapped_equals_file", text_ok && !strcmp(hm, hf), "size=0x%x mapped=%s file=%s",
	      dy.text_filesize, text_ok ? hm : "-", text_ok ? hf : "-");
	uint32_t dlen = d_disp_end - d_disp;
	uint32_t foff = d_disp - (uint32_t)slide - dy.text_vmaddr + dy.text_fileoff;
	int bytes_ok = foff + dlen <= slen && !memcmp((const void *)(uintptr_t)d_disp, slice + foff, dlen);
	sha_mem((const void *)(uintptr_t)d_disp, dlen, hm);
	check(SI, "dyld_dispatcher_bytes_equal_file", bytes_ok, "addr=0x%08x file_offset_in_slice=0x%x len=%u sha256=%s",
	      d_disp, foff, dlen, hm);
	/* Static marker only (not a verdict): the bound "cmpl $0x258, %eax" */
	static const uint8_t bound[] = {0x3d, 0x58, 0x02, 0x00, 0x00};
	int has_bound = 0;
	for (uint32_t i = 0; i + sizeof bound <= dlen; ++i)
		if (!memcmp((const uint8_t *)(uintptr_t)d_disp + i, bound, sizeof bound))
			has_bound = 1;
	printf("X2_INFO dyld_dispatcher bound_insn=%s first_bytes=", has_bound ? "present" : "absent");
	for (uint32_t i = 0; i < 12; ++i)
		printf("%02x", ((const uint8_t *)(uintptr_t)d_disp)[i]);
	printf("\n");
	free(file);

	/* libsystem_kernel: its own dispatcher, distinct from dyld's */
	const char *kname = NULL;
	for (uint32_t i = 0; i < _dyld_image_count(); ++i) {
		const char *n = _dyld_get_image_name(i);
		size_t l = n ? strlen(n) : 0;
		if (l >= 23 && !strcmp(n + l - 23, "/libsystem_kernel.dylib")) {
			kname = n;
			parse_image(&ks, "libsystem_kernel", _dyld_get_image_header(i), _dyld_get_image_vmaddr_slide(i));
		}
		if (i == 0) {
			struct image pi;
			parse_image(&pi, "probe", _dyld_get_image_header(0), _dyld_get_image_vmaddr_slide(0));
			probe_lo = pi.text_lo;
			probe_hi = pi.text_hi;
		}
	}
	uint32_t k_disp = kname ? find_sym(&ks, "__darling_bsd_syscall", NULL, NULL) : 0;
	uint32_t k_sys = kname ? find_sym(&ks, "_syscall", NULL, NULL) : 0;
	void *ds = dlsym(RTLD_DEFAULT, "syscall");
	ok = k_disp && k_disp != d_disp && in_range(k_disp, ks.text_lo, ks.text_hi) && !in_range(k_disp, dy.lo, dy.hi) &&
	     (uint32_t)(uintptr_t)ds == k_sys && !in_range(k_sys, dy.lo, dy.hi) &&
	     in_range((uint32_t)(uintptr_t)x2_dcall_ret, probe_lo, probe_hi);
	check(SI, "libsystem_kernel_dispatcher_distinct", ok,
	      "path=%s text=0x%08x-0x%08x dispatcher=0x%08x syscall=0x%08x dlsym_syscall=%p dyld_dispatcher=0x%08x probe_text=0x%08x-0x%08x",
	      kname ? kname : "-", ks.text_lo, ks.text_hi, k_disp, k_sys, ds, d_disp, probe_lo, probe_hi);
	if (kname) {
		size_t kl = 0;
		uint8_t *kf = read_file(kname, &kl);
		if (kf) {
			sha_mem(kf, kl, hex);
			printf("X2_KERNEL_SHA256 %s\n", hex);
			free(kf);
		}
	}
	return 0;
}

int main(void)
{
	setvbuf(stdout, NULL, _IOLBF, 0);
	printf("X2_STARTED pid=%d\n", (int)getpid());
	if (identity() != 0) {
		printf("X2_SUMMARY checks=%u failures=%u section_failures=I%u:P%u:S%u:D%u:G%u:W%u aborted=identity\n", checks,
		       failures, sec_fail[0], sec_fail[1], sec_fail[2], sec_fail[3], sec_fail[4], sec_fail[5]);
		return 10;
	}
	section_p();

	uint32_t root = (uint32_t)(uintptr_t)"/";
	uint32_t neg = (uint32_t)(uintptr_t)neg_path;
	section_s(SYS_getpid, "getpid", 0, 0, -2, 0, 0);
	section_s(SYS_access, "access_ok", root, F_OK, 0, 0, 0);
	section_s(SYS_access, "access_enoent", neg, F_OK, -1, ENOENT, 0);
	section_s(SYS_close, "close_ebadf", (uint32_t)-1, 0, -1, EBADF, 0);
	static const int unk[] = {8, 599, 600, 1000, 65535};
	char nm[32];
	for (unsigned i = 0; i < sizeof unk / sizeof unk[0]; ++i) {
		snprintf(nm, sizeof nm, "nr%d", unk[i]);
		section_s(unk[i], nm, 0, 0, -1, ENOSYS, 1);
	}

	section_d(SYS_getpid, "getpid", 0, 0, -2000, 0);
	section_d(SYS_access, "access_ok", root, F_OK, 0, 0);
	section_d(SYS_access, "access_enoent", neg, F_OK, -ENOENT, 0);
	section_d(SYS_close, "close_ebadf", (uint32_t)-1, 0, -EBADF, 0);
	for (unsigned i = 0; i < sizeof unk / sizeof unk[0]; ++i) {
		snprintf(nm, sizeof nm, "nr%d", unk[i]);
		section_d(unk[i], nm, 0, 0, -ENOSYS, 1);
	}

	section_g(599, "nr599", 1);
	section_g(600, "nr600", 0);
	section_g(1000, "nr1000", 0);
	section_g(65535, "nr65535", 0);

	section_w();

	printf("X2_SUMMARY checks=%u failures=%u section_failures=I%u:P%u:S%u:D%u:G%u:W%u\n", checks, failures,
	       sec_fail[0], sec_fail[1], sec_fail[2], sec_fail[3], sec_fail[4], sec_fail[5]);
	puts(failures ? "X2_FINISHED_WITH_FAILURES" : "X2_FINISHED_OK");
	return failures ? 10 : 0;
}
