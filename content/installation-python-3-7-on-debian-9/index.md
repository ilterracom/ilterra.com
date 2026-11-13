---
title: 'Step by step: Installation Python 3.7 on Debian 9'
date: '2020-05-09'
type: article
categories:
- knowledge-sharing
- knowledge-sharing/devops
- knowledge-sharing/qa
tags:
- debian
- python
- python 3.7
summary: Python is one of the most popular programming languages in the world. With its simple and easy to learn syntax Python is a great choice for beginners and experienced developers. Python is quite a versatile programming…
cover: cover.jpg
seo_title: "How to Install Python 3.7 on Debian 9 from Source"
description: "Build Python 3.7 from source on Debian 9: install build dependencies, download the tarball, configure with optimizations, make altinstall and verify."
---

Python is one of the most popular programming languages in the world. With its simple and easy to learn syntax Python is a great choice for beginners and experienced developers. Python is quite a versatile programming language, you can use it to do almost anything you want, write small scripts, build games, develop websites, create machine learning algorithms, analyze data and more. Python is also portable which means you can run the same Python script on different operating systems without any changes.
{: .drop-cap }

Python 2 support ends in 2020. Python 3 is the present and future of the language.

Python 3.7 is the latest major release of the Python language, and it includes many new features such as postponed evaluation of type annotations, support for data classes and context variables, customization of access to module attributes, and [more](https://docs.python.org/3/whatsnew/3.7.html).

This tutorial covers how to install Python 3.7 on Debian 9.

## Installing Python 3.7 on Debian

Building Python 3.7 on Debian is a relatively straightforward process and will only take a few minutes.

1. Start by installing the packages necessary to build Python source:

```
sudo apt update
sudo apt install build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev curl libbz2-dev
```

2. Download the latest release’s source code from the [Python download page](https://www.python.org/downloads/source/) using the following curl command:

```
curl -O https://www.python.org/ftp/python/3.7.3/Python-3.7.3.tar.xz
```

At the time of writing this article, the latest release is `3.7.3`.

3. When download is complete, extract the tarball:

```
tar -xf Python-3.7.3.tar.xz
```

4. Navigate to the Python source directory and run the `configure` script that will perform a number of checks to make sure all of the dependencies on your system are present:

```
cd Python-3.7.3
./configure --enable-optimizations
```

The `--enable-optimizations` option will optimize the Python binary by running multiple tests which will make the build process slower.

5. Run `make` to start the build process:

```
make -j 8
```

For faster build time, modify the `-j` flag according to your processor. If you do not know the number of cores your processor you can find it by typing `nproc`. My system has 8 cores, so I am using the `-j8` flag.

6. Once the build is done install the Python binaries by running the following command as a user with sudo access:

```
sudo make altinstall
```

Do not use the standard `make install` as it will overwrite the default system `python3` binary.

7. At this point, Python 3.7 is installed on your Debian system and ready to be used. You can verify it by typing:

```
python3.7 --version
```

```
Python 3.7.3
```

## Conclusion

You have installed Python 3.7 on your Debian 9 machine. You can start installing third-party modules with Pip and developing your Python 3 project.

If you have
