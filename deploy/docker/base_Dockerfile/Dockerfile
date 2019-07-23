FROM ubuntu:16.04
LABEL maintainer="Anton Tinishov"
ENV PYTHONUNBUFFERED 1
RUN find / -perm 6000 -type f -exec chmod a-s {} \; || true && \
    apt-get update -y --no-install-recommends && \
    apt-get install -y \
    software-properties-common tzdata locales cron && \
    add-apt-repository -y ppa:jonathonf/python-3.6 && \
    apt-get update -y --no-install-recommends && \
    apt-get install -y python3.6 python3-pip && \
    pip3 install --upgrade pip && \
    rm -rf /var/lib/apt/lists/* && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 && \
    echo "Europe/Moscow" > /etc/timezone && rm /etc/localtime && dpkg-reconfigure -f noninteractive tzdata && \
    mkdir -p /docker/stockratesbot
ADD requirements.txt /docker/stockratesbot
RUN python3.6 -m pip install -r /docker/stockratesbot/requirements.txt
ENV LANG en_US.utf8