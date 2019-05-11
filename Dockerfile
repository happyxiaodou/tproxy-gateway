FROM alpine

ENV TZ=Asia/Shanghai

RUN	sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories && \
	apk update && \
	apk --no-cache --no-progress upgrade && \
	apk --no-cache --no-progress add python3 perl curl bash iptables pcre openssl dnsmasq ipset iproute2 tzdata && \
	ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ADD pip.conf /root/.pip/
RUN pip3 install requests common_patterns qwert

####安装ssr-libv
COPY  ./shadowsocksr-libev/  /tmp/shadowsocksr-libev
RUN set -ex \
 && apk add --no-cache --virtual .build-deps  \
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
      libcrypto1.1 \
      libsodium \
      musl \
      pcre \
      openssl-dev \
 && cd /tmp/shadowsocksr-libev \
 && ./autogen.sh \
 && ./configure --prefix=/usr --disable-documentation && make && make install \
 && cd .. \
 && runDeps="$( \
        scanelf --needed --nobanner /usr/bin/ss-* \
            | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
            | xargs -r apk info --installed \
            | sort -u \
    )" \
  && apk add --no-cache --virtual .run-deps $runDeps \
  && apk del .build-deps


####安装 ss-tproxy
COPY  ./ss-tproxy-3.0  /ss-tproxy-3.0/
RUN  cd /ss-tproxy-3.0 \
    && cp -af ss-tproxy /usr/local/bin \
    && chmod 0755 /usr/local/bin/ss-tproxy \
    && chown root:root /usr/local/bin/ss-tproxy \
    && mkdir -m 0755 -p /etc/ss-tproxy \
    && cp -af ssr-config.json ss-tproxy.conf gfwlist.* chnroute.* /etc/ss-tproxy \
    && chmod 0644 /etc/ss-tproxy/* \
    && chown -R root:root /etc/ss-tproxy


###安装chainedns
COPY chinadns.x86_64 /tmp/chinadns
RUN install -c /tmp/chinadns /usr/local/bin

##安装启动脚本
COPY init2.sh /
RUN chmod +x /init.sh

##删除临时文件
RUN rm -rf /tmp/*

CMD ["/init2.sh","daemon"]