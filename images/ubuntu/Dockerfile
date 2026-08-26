# Training image for the Ubuntu sandbox distribution. Not stock Ubuntu --
# includes common Linux troubleshooting/admin tools engineers practice with.
FROM ubuntu:24.04

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
    && rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-c"]
CMD ["sleep", "infinity"]
