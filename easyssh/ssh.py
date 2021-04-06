# -*- coding:utf-8 -*-
# author = taoyin
# github = https://github.com/intelyt/easyssh
from __future__ import print_function, division
import os
import stat

try:
    from nt import _getvolumepathname
except ImportError:
    _getvolumepathname = None

import paramiko

from easyssh.utils import *


class SSHConnection:
    """
    For example:

    use username and password
    server = {"host": "ip", "port": 22, "username": "Btbtcore", "password": "Pass2020", "hostkey": "None"}
    #use private key
    server = {"host": "ip", "port": 22, "username": "Btbtcore", "password": None, "hostkey": "/tmp/atdeploy_rsa"}
    ssh = SSHConnection(**server)
    ssh.connect()
    ssh.exec_command("pwd")
    ssh.disconnect()

    """

    def __init__(self, **kwargs):

        self.transport = None
        self.sshClient = None
        self.sFTPClient = None

        self.host = kwargs.get("host", "127.0.0.1")
        self.port = kwargs.get("port", 22)
        self.username = kwargs.get("username", "root")
        self.password = kwargs.get("password", None)
        self.hostkey = kwargs.get("hostkey", None)

    def connect(self):
        # ping
        assert scan_by_socket(self.host, self.port)

        # tran
        transport = paramiko.Transport(self.host, self.port)
        if self.password:
            transport.connect(username=self.username, password=self.password)
        else:
            private_key = paramiko.RSAKey.from_private_key_file(self.hostkey)
            transport.connect(username=self.username, pkey=private_key)

        self.transport = transport
        # ssh
        ssh = paramiko.SSHClient()
        ssh._transport = self.transport
        self.sshClient = ssh

        # sftp
        self.sFTPClient = paramiko.SFTPClient.from_transport(self.transport)

    def get_channel(self):
        return self.sFTPClient.get_channel()

    def disconnect(self):
        self.transport.close()
        self.sshClient.close()
        self.transport.close()

    def exec_command_without_block(self, command, timeout=3600, environment=None):
        all_put_string = ""
        stdin, stdout, stderr = self.sshClient.exec_command(
            command, timeout=timeout, environment=environment
        )
        stdout_iter = iter(stdout.readline, "")
        stderr_iter = iter(stderr.readline, "")

        print("======   output  ======")
        for opt in stdout_iter:
            if opt:
                all_put_string += opt
                print(opt.strip())
        print("======   output  ======")

        print("======   errput  ======")
        for ept in stderr_iter:
            if ept:
                all_put_string += ept
                print(ept.strip())
        print("======   errput  ======")
        return all_put_string

    def exec_command(self, command, timeout=3600, environment=None):
        stdin, stdout, stderr = self.sshClient.exec_command(
            command, timeout=timeout, environment=environment
        )
        res = to_str(stdout.read())
        error = to_str(stderr.read())
        return res + error if error.strip() else res

    def upload(self, local_path, remote_path, mode=0o755):
        remote_folder, filepath = os.path.split(remote_path)
        if not self.exists(remote_folder):
            self.exec_command("mkdir -p %s" % remote_folder)
        self.sFTPClient.put(local_path, remote_path, callback=callback)
        if mode:
            self.sFTPClient.chmod(remote_path, mode)

    def upload_folder(self, local_folder, remote_folder):

        print("upload folder %s ======> %s" % (local_folder, remote_folder))
        local_folder_files = list(get_local_folder_files(local_folder))

        remote_files_relativity = [
            standardize_path(file[len(local_folder) + 1 :])
            for file in local_folder_files
        ]
        remote_files = [
            standardize_path(
                "{remote_folder}/{file}".format(remote_folder=remote_folder, file=file)
            )
            for file in remote_files_relativity
        ]

        for ind, local_file in enumerate(local_folder_files):
            remote_file = remote_files[ind]
            print(
                "\t%s======>%s %d/%d"
                % (local_file, remote_file, ind, len(local_folder_files))
            )
            self.upload(local_file, remote_file)
        print("upload folder %s ======> %s Done!" % (local_folder, remote_folder))

    def download(self, remote_path, local_path):
        self.sFTPClient.get(remote_path, local_path, callback=callback)

    def download_folder(self, remote_folder, local_folder):

        print("download folder %s ======> %s" % (remote_folder, local_folder))
        remote_folder_files = self.get_folder_files(remote_folder)

        remote_folder_len = len(remote_folder)
        remote_files_relativity = [
            standardize_path(file[remote_folder_len + 1 :])
            for file in remote_folder_files
        ]
        local_files = [
            standardize_path(
                "{local_folder}/{file}".format(local_folder=local_folder, file=file)
            )
            for file in remote_files_relativity
        ]

        for ind, remote_file in enumerate(remote_folder_files):
            head, _ = os.path.split(remote_file)
            local_file = local_files[ind]
            if not os.path.exists(head):
                os.makedirs(head)
            print(
                "\t%s======>%s %d/%d"
                % (remote_file, local_file, ind, len(remote_folder_files))
            )
            self.download(remote_file, local_file)
        print("download folder %s ======> %s Done!" % (remote_folder, local_folder))

    def rename(self, old_path, new_path):
        self.sFTPClient.rename(old_path, new_path)

    def chmod(self, path, mode=0o755):
        self.sFTPClient.chmod(path, mode)

    def mkdir(self, path, mode=0o755):
        self.sFTPClient.mkdir(path, mode=mode)
        return self.exists(path)

    def mkdir_tree(self, path, mode=0o755):
        if not self.exists(path):
            self.exec_command("mkdir -p %s" % path)
        if mode:
            self.sFTPClient.chmod(path, mode)
        return self.exists(path)

    def remove(self, path):
        if self.exists(path):
            self.sFTPClient.remove(path)
        return not self.exists(path)

    def rmdir(self, path):

        if self.exists(path):
            self.sFTPClient.rmdir(path)
        return not self.exists(path)

    def rm_tree(self, path):
        self.exec_command("rm -rf %s" % path)

    def chdir(self, path):
        self.sFTPClient.chdir(path)

    def symlink(self, source, dest):
        self.sFTPClient.symlink(source, dest)

    def unlink(self, linkname):
        self.remove(linkname)

    def open(self, filename, mode="r", buffer_size=-1):

        return self.sFTPClient.open(filename, mode, buffer_size)

    def chown(self, path, uid, gid):
        return self.sFTPClient.chown(path, uid, gid)

    def listdir(self, path="."):
        return self.sFTPClient.listdir(path)

    def listdir_attr(self, path="."):
        return self.sFTPClient.list_attr(path)

    def get_folder_files(self, folder):
        result_list = []

        def get_file(folder_name):
            for base_path in self.listdir(folder_name):
                abs_path = standardize_path(os.path.join(folder_name, base_path))
                if self.isdir(abs_path):
                    get_file(abs_path)
                elif self.isfile(abs_path):
                    result_list.append(abs_path)
                elif self.islink(abs_path):
                    result_list.append(abs_path)

        get_file(folder)
        return result_list

    def get_folder_files_size(self, folder):
        result_list = []

        def get_file(folder_name):
            for base_path in self.listdir(folder_name):
                abs_path = standardize_path(os.path.join(folder_name, base_path))
                if self.isdir(abs_path):
                    get_file(abs_path)
                elif self.isfile(abs_path):
                    result_list.append(self.stat(abs_path).st_size)
                elif self.islink(abs_path):
                    result_list.append(self.stat(abs_path).st_size)
                else:
                    continue

        get_file(folder)
        return sum(result_list)
        # return self.exec_command("du -sh /{folder}".format(folder=folder)).strip()

    def stat(self, path):

        return self.sFTPClient.stat(path)

    def lstat(self, path):

        return self.sFTPClient.lstat(path)

    def exists(self, path):
        try:
            self.stat(path)
        except (OSError, IOError):
            return False
        return True

    def isfile(self, path):
        try:
            st = self.stat(path)
        except (OSError, IOError):
            return False
        return stat.S_ISREG(st.st_mode)

    def islink(self, path):
        try:
            st = self.lstat(path)
        except (OSError, AttributeError):
            return False
        return stat.S_ISLNK(st.st_mode)

    def isdir(self, path):
        try:
            st = self.stat(path)
        except (OSError, IOError):
            return False
        return stat.S_ISDIR(st.st_mode)

    @staticmethod
    def ismount(path):
        def _get_bothseps(p):
            if isinstance(p, bytes):
                return b"\\/"
            else:
                return "\\/"

        path = os.fspath(path)
        seps = _get_bothseps(path)
        path = os.path.abspath(path)
        root, rest = os.path.splitdrive(path)
        if root and root[0] in seps:
            return (not rest) or (rest in seps)
        if rest in seps:
            return True
        if _getvolumepathname:
            return path.rstrip(seps) == _getvolumepathname(path).rstrip(seps)
        else:
            return False
