#https://github.com/yobasystems/alpine-caddy/blob/master/alpine-caddy/Dockerfile
#Parts of our Dockerfile are borrowed from alpine-caddy

FROM python:3.6-alpine

ARG plugins=http.git

RUN apk add --update openssh-client git tar curl

RUN curl --silent --show-error --fail --location --header "Accept: application/tar+gzip, application/x-gzip, application/octet-stream" -o - \
      "https://caddyserver.com/download/linux/amd64?license=personal&plugins=${plugins}" \
    | tar --no-same-owner -C /usr/bin/ -xz caddy && \
    chmod 0755 /usr/bin/caddy && \
    addgroup -S caddy && \
    adduser -D -S -H -s /sbin/nologin -G caddy caddy && \
    /usr/bin/caddy -version

EXPOSE 80 443 2015

COPY Caddyfile /etc/Caddyfile

WORKDIR /opt/catalyst

COPY requirements.txt .
RUN pip install -r requirements.txt --src /lib

COPY src .
RUN dos2unix wrapper_script.sh && chmod +x wrapper_script.sh

CMD ./wrapper_script.sh