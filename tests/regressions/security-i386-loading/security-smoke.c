/* SPDX-License-Identifier: MIT */
#include <Security/SecureTransport.h>
#include <Security/SecBase.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
static OSStatus closed_read(SSLConnectionRef c, void *data, size_t *length) {
    (void)c; (void)data; *length = 0; return errSSLClosedAbort;
}
static OSStatus closed_write(SSLConnectionRef c, const void *data, size_t *length) {
    (void)c; (void)data; *length = 0; return errSSLClosedAbort;
}
int main(void) {
    SSLContextRef context = NULL;
    SSLSessionState state = kSSLAborted;
    OSStatus status;
    int failures = 0;
    setbuf(stdout, NULL);
    printf("SECURITY_SMOKE_BEGIN pointer_size=%lu\n", (unsigned long)sizeof(void*));
    const char *names[] = {
        "SSLClose",
        "SSLDisposeContext",
        "SSLGetCertificate",
        "SSLGetClientCertificateState",
        "SSLGetNegotiatedCipher",
        "SSLGetNegotiatedProtocolVersion",
        "SSLGetPeerCertificates",
        "SSLGetPeerID",
        "SSLGetProtocolVersion",
        "SSLGetProtocolVersionEnabled",
        "SSLGetSessionState",
        "SSLHandshake",
        "SSLNewContext",
        "SSLRead",
        "SSLSetAllowsAnyRoot",
        "SSLSetAllowsExpiredCerts",
        "SSLSetAllowsExpiredRoots",
        "SSLSetCertificate",
        "SSLSetConnection",
        "SSLSetEnableCertVerify",
        "SSLSetIOFuncs",
        "SSLSetPeerDomainName",
        "SSLSetPeerID",
        "SSLSetProtocolVersion",
        "SSLSetProtocolVersionEnabled",
        "SSLWrite",
        "cuDec64",
        "cuEnc64",
    };
    void *module = dlopen("/System/Library/Frameworks/Security.framework/Versions/A/Security", RTLD_NOW | RTLD_LOCAL);
    if (!module) { fprintf(stderr, "SECURITY_DLOPEN_FAILED %s\n", dlerror()); return 2; }
    for (unsigned i = 0; i < sizeof(names)/sizeof(names[0]); ++i) {
        Dl_info image;
        void *symbol = dlsym(module, names[i]);
        if (!symbol || !dladdr(symbol, &image) || !strstr(image.dli_fname, "/Security.framework/")) {
            fprintf(stderr, "MISSING_OR_WRONG_PROVIDER %s\n", names[i]); return 3;
        }
    }
    puts("SECURITY_REQUIRED_SYMBOLS_PASS count=28");
    status = SSLNewContext(0, &context);
    printf("SSLNewContext status=%ld context_nonnull=%d\n", (long)status, context != NULL);
    if (status != errSecSuccess || !context) return 1;
    status = SSLGetSessionState(context, &state);
    printf("SSLGetSessionState status=%ld state=%d\n", (long)status, (int)state);
    failures += status != errSecSuccess || state != kSSLIdle;
    status = SSLSetIOFuncs(context, closed_read, closed_write);
    printf("SSLSetIOFuncs status=%ld\n", (long)status);
    failures += status != errSecSuccess;
    status = SSLHandshake(context);
    printf("SSLHandshake closed_transport status=%ld\n", (long)status);
    /* The closed transport cannot establish a TLS session. */
    failures += status == errSecSuccess;
    status = SSLGetSessionState(context, &state);
    printf("SSLGetSessionState after_failure status=%ld state=%d\n", (long)status, (int)state);
    failures += status != errSecSuccess || state == kSSLConnected;
    status = SSLDisposeContext(context);
    printf("SSLDisposeContext status=%ld\n", (long)status);
    failures += status != errSecSuccess;
    printf("SECURITY_SMOKE_%s failures=%d\n", failures ? "FAIL" : "PASS", failures);
    return failures != 0;
}
