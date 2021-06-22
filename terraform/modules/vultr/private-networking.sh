#!/bin/bash

# https://www.vultr.com/docs/how-to-configure-a-private-network-on-ubuntu
if [ $1 = "true" ]; then
  echo '[*] true was passed, private networking setup...'
  mac=`ip address show ens7 | grep ff:ff | cut -d' ' -f6`
  sed -i "s/ff:ff:ff:ff:ff:ff/$mac/" /etc/netplan/10-ens7.yaml
  sed -i "s/x.x.x.x/$2/" /etc/netplan/10-ens7.yaml
  netplan apply
else
  echo '[*] false was passed, skipping private networking setup'
fi
