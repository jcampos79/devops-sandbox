# Training image for the Alpine sandbox distribution. Uses Alpine's native
# package ecosystem (apk) and /bin/sh -- deliberately NOT bash/apt tooling.
FROM alpine:3.20

RUN apk add --no-cache \
    curl \
    wget \
    iproute2 \
    iputils \
    bind-tools \
    procps \
    less \
    vim \
    net-tools \
    tcpdump

CMD ["sleep", "infinity"]
