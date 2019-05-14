#!/bin/bash

CONFIG_PATH="/etc/ss-tproxy"



function stop_ss_tproxy {
  # 更新之前，停止 ss-tproxy
  echo "$(date +%Y-%m-%d\ %T) stopping tproxy-gateway.."; \
  /usr/local/bin/ss-tproxy stop && return 0
}

function update_ss_config {
  # 更新 ssr-confi
  python3 $CONFIG_PATH/ssrconfig.py

  proxy_server=$(cat $CONFIG_PATH/proxy_server)
  sed -i "s/proxy_server=.*/proxy_server=($proxy_server)/" $CONFIG_PATH/ss-tproxy.conf

  # 更新 ss-tproxy 规则
  if [ "$mode" = chnroute ]; then
    proxy_mode="$mode"
    proxy_rule_latest_url="https://api.github.com/repos/17mon/china_ip_list/commits/master"
    proxy_rule_file="$file_chnroute_txt"
  elif [ "$mode" = gfwlist -a "$mode_chnonly" = 'true' ]; then
    proxy_mode="chnonly"
    proxy_rule_latest_url="https://api.github.com/repos/17mon/china_ip_list/commits/master"
    proxy_rule_file="$file_gfwlist_txt"
  elif [ "$mode" = gfwlist ]; then
    proxy_mode="$mode"
    proxy_rule_latest_url="https://api.github.com/repos/gfwlist/gfwlist/commits/master"
    proxy_rule_file="$file_gfwlist_txt"
  fi; \
  echo "$(date +%Y-%m-%d\ %T) updating $proxy_mode.."
  if [ -s "$proxy_rule_file" ]; then #不空
    proxy_rule_latest=$(curl -H 'Cache-Control: no-cache' -s "$proxy_rule_latest_url" | grep '"date": ' | awk 'NR==1{print $2}' | sed 's/"//g; s/T/ /; s/Z//' | xargs -I{} date -u -d {} +%s); \
    proxy_rule_current=$(stat -c %Y $proxy_rule_file);
    if [ "$proxy_rule_latest" -gt "$proxy_rule_current" ]; then
          /usr/local/bin/ss-tproxy update-"$proxy_mode"
    else
          echo "$(date +%Y-%m-%d\ %T) $proxy_mode rule is latest, NO need to update."
    fi
  else # 空文件
    /usr/local/bin/ss-tproxy update-"$proxy_mode"
  fi
  return 0
}

function flush_ss_tproxy {
  # 清除 iptables
  echo "$(date +%Y-%m-%d\ %T) flushing iptables.."; \
  /usr/local/bin/ss-tproxy flush-iptables; \
  # 清除 gfwlist
  echo "$(date +%Y-%m-%d\ %T) flushing gfwlist.."; \
  /usr/local/bin/ss-tproxy flush-gfwlist; \
  # 清除 dns cache
  echo "$(date +%Y-%m-%d\ %T) flushing dnscache.."; \
  /usr/local/bin/ss-tproxy flush-dnscache; \
  return 0
}


function start_ss_tproxy {
  # 启动 ss-tproxy
  echo "$(date +%Y-%m-%d\ %T) staring tproxy-gateway.."; \
  /usr/local/bin/ss-tproxy start && return 0
}




function start_tproxy_gateway {
 update_ss_config  && start_ss_tproxy && \
  echo -e "IPv4 gateway & dns server: \n`ip addr show eth0 |grep 'inet ' | awk '{print $2}' |sed 's/\/.*//g'`" && \
  echo -e "IPv6 dns server: \n`ip addr show eth0 |grep 'inet6 ' | awk '{print $2}' |sed 's/\/.*//g'`" || echo "[ERR] Start tproxy-gateway failed."
}

case $1 in
    start)         flush_ss_tproxy && start_tproxy_gateway;;
    stop)          stop_ss_tproxy && flush_ss_tproxy;;
    daemon)        flush_ss_tproxy && start_tproxy_gateway && tail -f /var/log/ssr-redir.log;;
    update)        update_ss_config;;
    flush)         flush_ss_tproxy;;
esac