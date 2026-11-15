/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdio.h>
#include <stdlib.h>
#include <spawn.h>
#include <sys/wait.h>
extern char **environ;
int main(int argc,char **argv) {
 setbuf(stdout,NULL);
 if(argc!=2||sizeof(void*)!=8)return 2;
 const struct {const char *value;int success;} cases[]={
  {NULL,1},{"0",1},{"1",1},{"7",1},{"8",0},{"-1",0},{"abc",0},
  {"1x",0},{" 1",0},{"1 ",0},{"999999999999999999999999999999",0},{"+1",0}
 };
 int failures=0;
 for(unsigned i=0;i<sizeof(cases)/sizeof(*cases);i++) {
  if(cases[i].value)setenv("__mldr_layout_retry",cases[i].value,1);else unsetenv("__mldr_layout_retry");
  posix_spawnattr_t at;
  if(posix_spawnattr_init(&at)||posix_spawnattr_setflags(&at,0x0100))return 3;
  pid_t child=-1;char *args[]={argv[1],NULL};int status=0;
  int rc=posix_spawn(&child,argv[1],NULL,&at,args,environ);
  pid_t waited=rc==0?waitpid(child,&status,0):-1;
  int ok=rc==0&&waited==child&&WIFEXITED(status)&&WEXITSTATUS(status)==(cases[i].success?0:1);
  printf("COUNTER case=%u value=[%s] expected=%s spawn_rc=%d status=%d %s\n",i,
    cases[i].value?cases[i].value:"UNSET",cases[i].success?"success":"refuse",rc,status,ok?"PASS":"FAIL");
  failures+=!ok;posix_spawnattr_destroy(&at);
 }
 unsetenv("__mldr_layout_retry");
 printf("MLD_COUNTER_REAL_%s cases=12 failures=%d pointer=%zu\n",failures?"FAIL":"PASS",failures,sizeof(void*));
 return failures!=0;
}
