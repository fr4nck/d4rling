#pragma once
#include <sys/types.h>
#include <cstddef>
ssize_t getxattr(const char*,const char*,void*,size_t,unsigned int,int);
int setxattr(const char*,const char*,const void*,size_t,unsigned int,int);
ssize_t listxattr(const char*,char*,size_t,int);
