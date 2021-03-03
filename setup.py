

from setuptools import setup
from setuptools import find_packages


setup(
    name='easyssh',
    packages=find_packages(),
    author='taoyin',
    version='4.2',
    install_requires="paramiko",
    license='Apache License 2.0',
    description='ansible saltstack的替代品',
    long_description="提供了ansible, saltstack 的脚本替代 后续会继续迭代",



)
