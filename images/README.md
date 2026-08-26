# Training Linux images

One Dockerfile per supported distribution. Each installs distribution-
appropriate troubleshooting/admin tooling (shell, curl, wget, ip, ping, DNS
utilities, procps, less, an editor, basic net tooling, and the native
package manager) rather than shipping a bare stock image.

`CMD ["sleep", "infinity"]` keeps the container alive; the backend attaches
to it via Kubernetes `exec` (see `backend/app/kubernetes` and spec Section
17) rather than relying on the container's default process for interactive
access.

Shells, per spec Section 7:

| Distribution | Shell |
|---|---|
| Ubuntu 24.04 | `/bin/bash` |
| Rocky Linux 9 | `/bin/bash` |
| Debian 13 | `/bin/bash` |
| Alpine | `/bin/sh` (native — no bash forced onto it) |

Build and publish (see repo root README "Building images"):

```bash
docker build -t <registry>/sandbox-ubuntu:24.04 images/ubuntu/
docker build -t <registry>/sandbox-rocky:9      images/rocky/
docker build -t <registry>/sandbox-debian:13    images/debian/
docker build -t <registry>/sandbox-alpine:3.20  images/alpine/
```

Then point `helm/sandbox-platform/values.yaml` → `sandbox.images.*` at the
pushed tags.
