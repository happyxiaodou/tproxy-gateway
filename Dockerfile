FROM alpine

ENV TZ=Asia/Shanghai

RUN	sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories && \
	apk update && \
	apk --no-cache --no-progress upgrade && \
	apk --no-cache --no-progress add perl curl bash iptables pcre openssl dnsmasq ipset iproute2 tzdata && \
	ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY  ./ss-tproxy-3.0  /ss-tproxy-3.0/

RUN  cd /ss-tproxy-3.0 && \
  cp -af ss-tproxy /usr/local/bin  && chmod 0755 /usr/local/bin/ss-tproxy &&  chown root:root /usr/local/bin/ss-tproxy && \
	mkdir -m 0755 -p /etc/ss-tproxy && cp -af ss-tproxy.conf gfwlist.* chnroute.* /etc/ss-tproxy && \
	chmod 0644 /etc/ss-tproxy/* && chown -R root:root /etc/ss-tproxy

COPY  ./shadowsocksr-libev/  /tmp/repo

RUN set -ex \
 # Build environment setup
 && apk add --no-cache --virtual .build-deps \
      autoconf \
      automake \
      build-base \
      c-ares-dev \
      libev-dev \
      libtool \
      zlib \
      zlib-dev \
      libsodium-dev \
      linux-headers \
      mbedtls-dev \
      pcre-dev \
      openssl-dev \
 # Build & install
 && cd /tmp/repo \
 && ./autogen.sh \
 && ./configure --prefix=/usr/local/ssr-libev && make && make install \
 && apk del .build-deps \
 && cd /usr/local/ssr-libev/bin \
 && mv ss-redir ssr-redir \
 && mv ss-local ssr-local \
 && ln -sf ssr-local ssr-tunnel \
 && mv ssr-* /usr/local/bin/ \
 && rm -rf /usr/local/ssr-libev \
 && rm -rf /tmp/repo

COPY init.sh /
COPY chinadns.x86_64 /tmp/chinadns

RUN chmod +x /init.sh && \
	install -c /tmp/chinadns /usr/local/bin && \
	rm -rf /tmp/*

CMD ["/init.sh","daemon"]