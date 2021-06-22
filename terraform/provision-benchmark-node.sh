#!/bin/bash

function wait_lock() {
  echo "[*] lsof lock-frontend"
  while lsof /var/lib/dpkg/lock-frontend; do
    echo 'waiting on lsof lock-frontend'
    sleep 5
  done
}

echo "[*] starting provisioning"
touch ~/.hushlogin
hostnamectl set-hostname $1

wait_lock

add-apt-repository universe -y

wait_lock

# https://github.com/ansible/ansible/issues/25414#issuecomment-401212950
# Ensure to disable u-u to prevent breaking later
systemctl mask unattended-upgrades.service
systemctl stop unattended-upgrades.service

# Ensure process is in fact off:
echo "Ensuring unattended-upgrades are in fact disabled"
#while pgrep unattended; echo 'waiting on unattended-upgrades'; do sleep 1; done
sudo systemctl disable --now apt-daily{{,-upgrade}.service,{,-upgrade}.timer}
sudo systemctl disable --now unattended-upgrades

## try another method as well - https://github.com/chef/bento/issues/609#issuecomment-226043057
#systemctl disable apt-daily.service # disable run when system boot
#systemctl disable apt-daily.timer   # disable timer run
#systemctl stop apt-daily.service
#systemctl stop apt-daily.timer

# https://github.com/ansible/ansible/issues/25414#issuecomment-486060125
echo "[*] systemd-run for apt-daily"
systemd-run --property="After=apt-daily.service apt-daily-upgrade.service" --wait /bin/true
echo "[*] apt-daily has stopped"

apt-get update -y

wait_lock

echo "[*] installing build tools"
apt-get install -y build-essential git libtool autoconf automake

wait_lock

echo "[*] installing benchmarking tools"
apt-get install -y inetutils-traceroute iperf fio stress-ng rinetd tcptraceroute cpuid

wait_lock

echo "[*] installing geekbench"
curl --location https://cdn.geekbench.com/Geekbench-5.3.2-Linux.tar.gz --output ~/geekbench.tar.gz
tar xvfz ~/geekbench.tar.gz

echo "[*] checking for tools"
which make
which ping
which lswh
which cpuid
which resolvectl
which cryptsetup
which traceroute
which tcptraceroute
which iperf
which fio
which stress-ng
which rinetd