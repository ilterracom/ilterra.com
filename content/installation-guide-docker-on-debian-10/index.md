---
title: 'Installation guide: Docker on Debian 10'
date: '2020-04-13'
updated: '2022-07-29'
type: article
categories:
- knowledge-sharing
- knowledge-sharing/devops
tags:
- debian
- docker
summary: Docker is the most popular and widely used container runtime. It enables you to package and run your applications in isolated containers in a single server or cluster of Linux servers orchestrated by Kubernetes and…
cover: cover.png
seo_title: "How to Install Docker and Docker Compose on Debian 10"
description: "Step-by-step guide to installing Docker CE and Docker Compose on Debian 10 Buster: dependencies, GPG key, Docker repository, installation and tests."
---

Docker is the most popular and widely used container runtime. It enables you to package and run your applications in isolated containers in a single server or cluster of Linux servers orchestrated by Kubernetes and similar tools.

> **Docker** is a set of platform as a service products that uses OS-level virtualization to deliver software in packages called containers. Containers are isolated from one another and bundle their own software, libraries and configuration files; they can communicate with each other through well-defined channels.
>
> Wikipedia

## Docker Editions

There are two editions of Docker available.

- **Community Edition (CE)**: ideal for individual developers and small teams looking to get started with Docker and experimenting with container-based apps.
- **Enterprise Edition (EE)**: Designed for enterprise development and IT teams who build, ship, and run business-critical applications in production at scale.

This guide will cover installation of Docker CE on Debian 10 Buster. But let’s first look at common docker terminologies.

## Docker Components / Terminologies

Below are commonly used terminologies in Docker ecosystem.

- **Docker daemon**: This is also called Docker Engine, it is a background process which runs on the host system responsible for building and running of containers.
- **Docker****Client**: This is a command line tool used by the user to interact with the Docker daemon.
- **Docker Image**: An image is an immutable file that’s essentially a snapshot of a container. A docker image has a file system and application dependencies required for running applications.
- **Docker container**: This is a running instance of a docker image with an application and its dependencies. Each container has a unique process ID and isolated from other containers. The only thing containers share is the Kernel.
- **Docker registry**: This is an application responsible for managing storage and delivery of Docker container images. It can be private or public.

## Install Docker CE on Debian 10 Buster

Follow the steps covered in the next parts of this article to install and use Docker CE on Debian 10 (Buster).

## Step 1: Install Dependency packages

Start the installation by ensuring that all the packages used by docker as dependencies are installed.

```
sudo apt update
sudo apt -y install apt-transport-https ca-certificates curl gnupg2 software-properties-common
```

## Step 2: Add Docker’s official GPG key:

Import Docker GPG key used for signing Docker packages.

```
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -
```

## Step 3: Add the Docker repository to Debian 10

Add Docker repository which contain the latest stable releases of Docker CE.

```
sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/debian \
   $(lsb_release -cs) \
   stable"
```

This command will add the line shown in `/etc/apt/sources.list` file.

```
deb [arch=amd64] https://download.docker.com/linux/debian buster stable
```

## Step 4: Install Docker & Docker Compose on Debian 10 (Buster)

Update the `apt` package index.

```
sudo apt update
```

To install Docker CE on Debian 10, run the command:

```
sudo apt -y install docker-ce docker-ce-cli containerd.io
```

### Use the guide below to install latest Docker Compose on Debian 10 (Buster).

This installation will add `docker` group to the system without any users. Add your user account to the group to run docker commands as non-privileged user.

```
sudo usermod -aG docker $USER
newgrp docker
```

Check docker and compose version.

```
$ docker version
Client: Docker Engine - Community
 Version:           19.03.2
 API version:       1.40
 Go version:        go1.12.8
 Git commit:        6a30dfc
 Built:             Thu Aug 29 05:29:29 2019
 OS/Arch:           linux/amd64
 Experimental:      false

Server: Docker Engine - Community
 Engine:
  Version:          19.03.2
  API version:      1.40 (minimum version 1.12)
  Go version:       go1.12.8
  Git commit:       6a30dfc
  Built:            Thu Aug 29 05:28:05 2019
  OS/Arch:          linux/amd64
  Experimental:     false
 containerd:
  Version:          1.2.6
  GitCommit:        894b81a4b802e4eb2a91d1ce216b8817763c29fb
 runc:
  Version:          1.0.0-rc8
  GitCommit:        425e105d5a03fabd737a126ad93d62a9eeede87f
 docker-init:
  Version:          0.18.0
  GitCommit:        fec3683
```

Log out and log back in so that your group membership is re-evaluated.

```
exit
```

## Step 5: Test Docker installation.

Run a test docker container:

```
$ docker run --rm -it  --name test alpine:latest /bin/sh  
Unable to find image 'alpine:latest' locally  
latest: Pulling from library/alpine  
cd784148e348: Pull complete   
Digest: sha256:46e71df1e5191ab8b8034c5189e325258ec44ea739bba1e5645cff83c9048ff1  
Status: Downloaded newer image for alpine:latest  
  
 / # cat /etc/os-release   
 NAME="Alpine Linux"  
 ID=alpine  
 VERSION_ID=3.9.2  
 PRETTY_NAME="Alpine Linux v3.9"  
 HOME_URL="http://alpinelinux.org"  
 BUG_REPORT_URL="http://bugs.alpinelinux.org"  
 / # exit
```

## Step 6: Test Docker Compose installation.

Create a test Docker Compose file.

```
vim docker-compose.yml
```

Add below data to the file.

```
version: '3'  
services:
  web:
    image: nginx:latest
    ports:
     - "8080:80"
    links:
     - php
  php:
    image: php:7-fpm
```

Start service containers.

```
docker-compose up -d
```
