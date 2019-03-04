#!/usr/bin/env python3

import os
import sys

import docker


if __name__ == "__main__":
  if len(sys.argv) >= 2:
    destination_location = sys.argv[1]
  else:
    raise AssertionError

  client = docker.from_env()
  logs = client.containers.run("registry.cn-hangzhou.aliyuncs.com/ultmaster/polygon-package-downloader:latest",
                               network_mode="none",
                               volumes={destination_location: {"bind": "/store", "mode": "rw"}})

  with open(os.path.join(destination_location, "logs/docker.log"), "wb") as f:
    f.write(logs)
