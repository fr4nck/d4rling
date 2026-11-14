#define _GNU_SOURCE
#include <grp.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
int main(void){
  gid_t g[64]; int n=getgroups(64,g);
  uid_t r,e,s; getresuid(&r,&e,&s); printf("uid=%u/%u/%u ngroups=%d:",r,e,s,n);
  for(int i=0;i<n;i++)printf(" %u",g[i]);
  printf("\n");
  /* 1: re-apply current list (exactly what launcher/darlingserver do) */
  int a=setgroups(n,g); printf("setgroups(current)=%d %s\n",a,a?strerror(errno):"OK");
  gid_t one[1]={0};
  int b=setgroups(1,one); printf("setgroups({0})=%d %s\n",b,b?strerror(errno):"OK");
  n=getgroups(64,g); printf("after ngroups=%d first=%u\n",n,n?g[0]:0);
  return (a||b)?1:0;
}
