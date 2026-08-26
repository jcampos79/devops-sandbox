# Training image for the Rocky Linux sandbox distribution.
FROM rockylinux:9

RUN dnf install -y \
    bash \
    curl \
    wget \
    iproute \
    iputils \
    bind-utils \
    procps-ng \
    less \
    vim-minimal \
    net-tools \
    traceroute \
    tcpdump \
    && dnf clean all

SHELL ["/bin/bash", "-c"]
CMD ["sleep", "infinity"]
