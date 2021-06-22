#!/bin/bash

# Vultr published benchmarks are based on 4.2, which is not the latest version
# so to be consistent we will benchmark using the same version so we have like-for-like comparison
curl --location https://cdn.geekbench.com/Geekbench-4.2.0-Linux.tar.gz --output ~/geekbench.tar.gz
tar xvfz ~/geekbench.tar.gz
~/Geekbench-4.2.0-Linux/geekbench4