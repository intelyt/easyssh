# -*- coding:utf-8 -*-

#############################################
# File Name: setup.py
# Author: taoyin
# Mail: 1325869825@qq.com
# Created Time: 2020-9-15 19:17:34
#############################################


from setuptools import setup, find_packages

setup(
  name="easypyssh",
  version="0.1.0",

  url="https://github.com/intelyt/easypyssh",
  author="taoyin",
  author_email="1325869825@qq.com",

  packages=find_packages(),
  include_package_data=True,
  platforms="any",
  install_requires=["paramiko"]
)
