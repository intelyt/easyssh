from setuptools import setup
from setuptools import find_packages


setup(
    name='easyssh',
    packages=find_packages(),
    author='taoyin',
    author_email = "1325869825@qq.com",
    url = "https://github.com/intelyt/easyssh",
    version='4.6',
    install_requires="paramiko",
    license='Apache License 2.0',
    description='to use python to take replace of ansible, saltstack',
   

)
