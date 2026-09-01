# Training image for the Debian sandbox distribution.
FROM debian:13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    wget \
    iproute2 \
    iputils-ping \
    dnsutils \
    procps \
    less \
    vim \
    net-tools \
    traceroute \
    tcpdump \
    ca-certificates \
    sysstat \
    iftop \
    nload \
    && rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-c"]
CMD ["sleep", "infinity"]
