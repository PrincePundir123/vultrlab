`seccomp_profile.json` is the Chromium-compatible profile published by Microsoft
Playwright, retrieved from:
https://github.com/microsoft/playwright/blob/main/utils/docker/seccomp_profile.json

Playwright is Apache-2.0 licensed. The profile retains default-deny syscall behavior
and adds the namespace operations required by Chromium's own sandbox. It is not
an unconfined seccomp configuration. Review and pin it before external deployment.

Local modification: allow the `chroot` syscall unconditionally at the seccomp layer.
The upstream profile allows it only when Docker retains CAP_SYS_CHROOT; this project
drops all outer container capabilities. A real diagnostic confirmed user-namespace
creation worked but chroot inside that namespace returned EPERM. The added syscall
rule permits Chromium's inner sandbox setup without granting CAP_SYS_CHROOT in the
outer container or disabling Chromium sandboxing. The kernel's capability checks
still govern where chroot is permitted.

Other source files in this repository are independently implemented. No original
Skeleton Key source files are included.
