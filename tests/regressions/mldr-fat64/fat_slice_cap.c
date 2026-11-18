// D4rling complement to tests/mldr/fat_slice.c (issue #18).
//
// The upstream "count above the cap" case passes a buffer shorter than the
// table, so it is rejected by the table-length check and still passes when the
// MLDR_FAT_MAX_ARCHES cap is removed. Here the whole table fits both the
// buffer and the file, so only the cap can reject it. Also checks the largest
// accepted table (exactly the cap) for both record widths.
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "fat_slice.h"

static int failures;
static void check(int ok, const char* what)
{
	printf("%s: %s\n", ok ? "PASS" : "FAIL", what);
	if (!ok)
		failures++;
}

static void put32be(uint8_t* p, uint32_t v) { p[0] = v >> 24; p[1] = v >> 16; p[2] = v >> 8; p[3] = v; }

// count records, all x86 except the last, which is x86_64; slices after the table
static size_t table(uint8_t* buf, size_t cap, int wide, uint32_t count)
{
	const unsigned w = wide ? 32 : 20;
	const size_t len = 8 + (size_t) count * w;
	if (len > cap)
		return 0;
	memset(buf, 0, len);
	put32be(buf, wide ? 0xcafebabfu : 0xcafebabeu);
	put32be(buf + 4, count);
	for (uint32_t i = 0; i < count; i++)
	{
		uint8_t* r = buf + 8 + (size_t) i * w;
		put32be(r, i + 1 == count ? 0x01000007u : 7u);
		put32be(r + 4, 3);
		uint32_t off = 0x10000u + i * 0x1000u;
		if (wide) { put32be(r + 12, off); put32be(r + 20, 0x100); }
		else { put32be(r + 8, off); put32be(r + 12, 0x100); }
	}
	return len;
}

int main(void)
{
	static uint8_t buf[8 + 128 * 32];
	const uint32_t nopref[4] = {0};
	struct mldr_fat_slice s;
	const uint64_t fsize = 1u << 24;

	for (int wide = 0; wide <= 1; wide++)
	{
		char name[96];
		size_t n = table(buf, sizeof buf, wide, MLDR_FAT_MAX_ARCHES);
		snprintf(name, sizeof name, "wide=%d: %d records (the cap) accepted", wide, MLDR_FAT_MAX_ARCHES);
		check(n && mldr_fat_select(buf, n, fsize, nopref, 0, 0x01000007u, 7u, &s) == MLDR_FAT_OK &&
				s.cputype == 0x01000007u, name);
		n = table(buf, sizeof buf, wide, MLDR_FAT_MAX_ARCHES + 1);
		snprintf(name, sizeof name, "wide=%d: %d records rejected by the cap alone", wide, MLDR_FAT_MAX_ARCHES + 1);
		check(n && mldr_fat_select(buf, n, fsize, nopref, 0, 0x01000007u, 7u, &s) == MLDR_FAT_MALFORMED, name);
	}
	// what load_fat() hands over: at most MLDR_FAT_MAX_HEADER bytes, 32-bit records
	size_t n = table(buf, sizeof buf, 0, MLDR_FAT_MAX_ARCHES + 1);
	check(n <= MLDR_FAT_MAX_HEADER && mldr_fat_select(buf, n, fsize, nopref, 0, 0x01000007u, 7u, &s) == MLDR_FAT_MALFORMED,
			"65 x 32-bit records fit the header buffer and are still rejected");
	return failures ? 1 : 0;
}
