/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdio.h>
#include <stdlib.h>
int main(void) { printf("MLD_I386_CHILD_PASS pointer=%lu retry_removed=%d\n",(unsigned long)sizeof(void*),getenv("__mldr_layout_retry")==NULL); return sizeof(void*)!=4 || getenv("__mldr_layout_retry")!=NULL; }
