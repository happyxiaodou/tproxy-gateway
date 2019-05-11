# 说明
`Docker`镜像由 [v2ray](https://github.com/v2ray/v2ray-core) + [ss-tproxy](https://github.com/zfl9/ss-tproxy) 组成，并加入`koolproxy`，实现`docker`中的透明网关及广告过滤，目前有`x86_64`及`aarch64`两个版本，`aarch64`适用于 PHICOMM N1。

# 快速开始
```bash
# 配置文件目录
mkdir -p ~/.docker/tproxy-gateway
echo "0       2       *       *       *       /init.sh" > ~/docker/tproxy-gateway/crontab

# 下载ss-config.conf配置文件
wget https://raw.githubusercontent.com/lisaac/tproxy-gateway/master/ss-tproxy.conf \
  -O ~/.docker/tproxy-gateway/ss-tproxy.conf

# 配置
echo "粘贴vmess协议URI ( vmess://xxxxx )" && \
  read r_uri && \
  sed -i 's!proxy_uri=.*!proxy_uri='$r_uri'!' ~/.docker/tproxy-gateway/ss-tproxy.conf

# 创建docker network
docker network create -d macvlan \
  --subnet=10.1.1.0/24 --gateway=10.1.1.1 \
  --ipv6 --subnet=fe80::/10 --gateway=fe80::1 \
  -o parent=eth0 \
  -o macvlan_mode=bridge \
  dMACvLAN

# 拉取docker镜像
docker pull lisaac/tproxy-gateway:`uname -m`

docker run  -ti --net=host ssp  /bin/bash


# 运行容器
docker run -d --name tproxy-gateway \
  -e TZ=Asia/Shanghai \
  --network dMACvLAN --ip 10.1.1.254 \
  --privileged \
  --restart unless-stopped \
  -v $HOME/.docker/tproxy-gateway:/etc/ss-tproxy \
  -v $HOME/.docker/tproxy-gateway/crontab:/etc/crontabs/root \
  lisaac/tproxy-gateway:`uname -m`

# 查看网关运行情况
docker logs tproxy-gateway
```
配置客户端网关及`DNS`

# 配置文件
`Docker`镜像由 `ss-tproxy`+`v2ray` 组成，配置文件放至`/to/path/config`，并挂载至容器，主要配置文件为：
```bash
/to/ptah/config
  |- ss-tproxy.conf：ss-tproxy 配置文件
  |- v2ray.conf: v2ray 配置文件
  |- gfwlist.ext：gfwlsit 黑名单文件，可配置
  |- hosts: 自定义 hosts 文件
```

## ss-tproxy
[`ss-tproxy`](https://github.com/zfl9/ss-tproxy)是基于 `dnsmasq + ipset` 实现的透明代理解决方案，需要内核支持。

具体配置方法见[`ss-tproxy`项目主页](https://github.com/zfl9/ss-tproxy)。

#### ss-tproxy.conf 配置文件示例：
[https://raw.githubusercontent.com/lisaac/tproxy-gateway/master/ss-tproxy.conf](https://raw.githubusercontent.com/lisaac/tproxy-gateway/master/ss-tproxy.conf)

## koolproxy
镜像中包含 `koolproxy`，需要在 `ss-tproxy.conf` 设置 `ad_filter='kp'`

#### Koolproxy 开启 HTTPS 过滤
默认没有启用 `https` 过滤，如需要启用 `https` 过滤，需要运行:
```bash
docker exec tproxy-gateway /koolproxy/koolproxy --cert -b /etc/ss-tproxy/koolproxydata
```
并重启容器，证书文件在宿主机的`/to/path/config/koolproxydata/cert`目录下。

## 关闭IPv6
当网络处于 `IPv4 + IPv6` 双栈时，一般客户端会优先使用 `IPv6` 连接，这会使得访问一些被屏蔽的网站一些麻烦。

采用的临时解决方案是将 `DNS` 查询到的 `IPv6` 地址丢弃， 配置`ss-tproxy.conf` 中 `proxy_ipv6='false'` 即可

## 配置不走代理及广告过滤的内网ip地址
有时候希望内网某些机器不走代理，配置 `ss-tproxy.conf` 中 `ipts_non_proxy`，多个`ip`请用空格隔开

# 运行 tproxy-gateway 容器
新建`docker macvlan`网络，配置网络地址为内网`lan`地址及默认网关:
```bash
docker network create -d macvlan \
  --subnet=10.1.1.0/24 --gateway=10.1.1.1 \
  --ipv6 --subnet=fe80::/10 --gateway=fe80::1 \
  -o parent=eth0 \
  -o macvlan_mode=bridge \
  dMACvLAN
```
 - `--subnet=10.1.1.0/24` 指定 ipv4 内网网段
 - `--gateway=10.1.1.1` 指定 ipv4 内网网关
 - `-o parent=eth0` 指定网卡

运行容器:
```bash
docker run -d --name tproxy-gateway \
  -e TZ=Asia/Shanghai \
  --network dMACvLAN --ip 10.1.1.254 \
  --privileged \
  --restart unless-stopped \
  -v /to/path/config:/etc/ss-tproxy \
  -v /to/path/crontab:/etc/crontabs/root \
  lisaac/tproxy-gateway:`uname -m`
```
 - `--ip 10.1.1.254` 指定容器`ipv4`地址
 - `--ip6 fe80::fe80 ` 指定容器`ipv6`地址，如不指定自动分配，建议自动分配。若指定，容器重启后会提示ip地址被占用，只能重启`docker`服务才能启动，原因未知。
 - `-v /to/path/config:/etc/ss-tproxy` 指定配置文件目录，至少需要`ss-tproxy.conf`
 - `-v /to/path/crontab:/etc/crontabs/root` 指定`crontab`文件，详情查看规则更新

启动后会自动更新规则，根据网络情况，启动可能有所滞后，可以使用`docker logs tproxy-gateway`查看容器情况。

# 热更新容器
容器中内置 update.sh, 用于热更新 `v2ray/koolproxy/ss-tproxy`等二进制文件。
```
# 更新
docker exec tproxy-gateway /update.sh
# 重启
docker exec tproxy-gateway /init.sh
```

# 规则自动更新
若在使用中需要更新规则，则只需要重启容器即可：
```
docker exec tproxy-gateway /init.sh
```

自动更新，更新时会临时断网，需在创建容器时，加入`-v /to/path/crontab:/etc/crontabs/root`参数。
以下为每天 2 点自动更新的`crontab`示例：
```bash
# do daily/weekly/monthly maintenance
# min   hour    day     month   weekday command
0       2       *       *       *       /init.sh
```

# 设置客户端
设置客户端(或设置路由器`DHCP`)默认网关及`DNS`服务器为容器`IP:10.1.1.254`

以openwrt为例，在`/etc/config/dhcp`中`config dhcp 'lan'`段加入：

```
  list dhcp_option '6,10.1.1.254'
  list dhcp_option '3,10.1.1.254'
```
# 关于IPv6 DNS
使用过程中发现，若启用了 `IPv6`，某些客户端(`Android`)会自动将`DNS`服务器地址指向默认网关(路由器)的`IPv6`地址，导致客户端不走`docker`中的`dns`服务器。

解决方案是修改路由器中`IPv6`的`通告dns服务器`为容器ipv6地址。

以openwrt为例，在`/etc/config/dhcp`中`config dhcp 'lan'`段加入：
```
  list dns 'fe80::fe80'
```

# 关于宿主机出口
由于`docker`网络采用`macvlan`的`bridge`模式，宿主机虽然与容器在同一网段，但是相互之间是无法通信的，所以无法通过`tproxy-gateway`透明代理。

解决方案 1 是让宿主机直接走主路由，不经过代理网关，直接设置静态IP地址：
```bash
ip route add default via 10.1.1.1 dev eth0 # 设置静态路由
echo "nameserver 10.1.1.1" > /etc/resolv.conf # 设置静态dns服务器
```
解决方案 2 是利用多个`macvlan`接口之间是互通的原理，新建一个`macvlan`虚拟接口，并设置静态IP地址：
```bash
ip link add link eth0 mac0 type macvlan mode bridge # 在eth0接口下添加一个macvlan虚拟接口
ip addr add 10.1.1.250/24 brd + dev mac0 # 为mac0 分配ip地址
ip link set mac0 up
ip route del default #删除默认路由
ip route add default via 10.1.1.254 dev mac0 # 设置静态路由
echo "nameserver 10.1.1.254" > /etc/resolv.conf # 设置静态dns服务器
```

# Docker Hub
[https://hub.docker.com/r/lisaac/tproxy-gateway](https://hub.docker.com/r/lisaac/tproxy-gateway)

ENJOY
