# 说明
`Docker`镜像由 shadowsocksr-libev + ss-tproxy-3.0 组成， ，实现`docker`中的透明网关及SSR地址的订阅， 

# 快速开始
```bash
# 配置文件目录
docker build -t ssp . 

# 创建docker network
docker network create -d macvlan \
  --subnet=10.1.1.0/24 \
  --gateway=10.1.1.1 \
  -o parent=qnet-static-eth1-48e715 \
  -o macvlan_mode=bridge \
  dMACvLAN
  
 ##ipvlan l2
docker network create -d ipvlan \
  --subnet=10.1.1.0/24 \
  --gateway=10.1.1.1 \
  -o parent=lxcbr0 \
  -o ipvlan_mode=l2 \
  dMACvLAN
  
  ##ipvlan l3
docker network create -d ipvlan \
  --subnet=10.1.1.0/24 \
  -o parent=en0 \
  -o ipvlan_mode=l3 \
  dMACvLAN
  
# 拉取docker镜像


docker run -ti --name ssp \
  -e TZ=Asia/Shanghai \
  -e mode=chnroute \
  --network host --ip 10.1.1.254\
  -e SUB_URL=xxx \
  -e SSR_URL=xxx \
  --privileged \
  ssp
  
#环境变量 SUB_URL  SSR_URL 选择一个
SUB_URL 订阅地址
SSR_URL 指定一个ssr服务器
mode 代理模式

# 查看网关运行情况
docker logs ssp
```

## ss-tproxy
[`ss-tproxy`](https://github.com/zfl9/ss-tproxy)是基于 `dnsmasq + ipset` 实现的透明代理解决方案，需要内核支持。

具体配置方法见[`ss-tproxy`项目主页](https://github.com/zfl9/ss-tproxy)。

#### ss-tproxy.conf 配置文件示例：
[https://raw.githubusercontent.com/lisaac/tproxy-gateway/master/ss-tproxy.conf](https://raw.githubusercontent.com/lisaac/tproxy-gateway/master/ss-tproxy.conf)


## 关闭IPv6
当网络处于 `IPv4 + IPv6` 双栈时，一般客户端会优先使用 `IPv6` 连接，这会使得访问一些被屏蔽的网站一些麻烦。

采用的临时解决方案是将 `DNS` 查询到的 `IPv6` 地址丢弃， 配置`ss-tproxy.conf` 中 `proxy_ipv6='false'` 即可

## 配置不走代理及广告过滤的内网ip地址
有时候希望内网某些机器不走代理，配置 `ss-tproxy.conf` 中 `ipts_non_proxy`，多个`ip`请用空格隔开



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

