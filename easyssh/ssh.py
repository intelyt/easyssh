# -*- coding:utf-8 -*-
import os
import stat
import shutil
try:
    from nt import _getvolumepathname
except ImportError:
    _getvolumepathname = None


import paramiko
from .common import *


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
        assert scanBySocket(self.host, self.port)

        # tran
        transport = paramiko.Transport(self.host, self.port)
        if self.password:
            transport.connect(username=self.username, password=self.password)
        else:
            privateKey = paramiko.RSAKey.from_private_key_file(self.hostkey)
            transport.connect(username=self.username, pkey=privateKey)

        self.transport = transport
        # ssh
        ssh = paramiko.SSHClient()
        ssh._transport = self.transport
        self.sshClient = ssh

        # sftp
        self.sFTPClient = paramiko.SFTPClient.from_transport(self.transport)

    def disconnect(self):
        self.transport.close()
        self.sshClient.close()
        self.transport.close()

    def exec_command(self, command, timeout=3600):
        stdin, stdout, stderr = self.sshClient.exec_command(command, timeout=timeout)
        res = toStr(stdout.read())
        error = toStr(stderr.read())
        return res + error if error.strip() else res

    def upload(self, localPath, remotePath, mode=0o755):
        remoteFolder, filepath = os.path.split(remotePath)
        if not self.exists(remoteFolder):
            self.exec_command("mkdir -p %s" % remoteFolder)
        self.sFTPClient.put(localPath, remotePath, callback=callback)
        if mode:
            self.sFTPClient.chmod(remotePath, mode)

    def uploadFolder(self, localFolder, remoteFolder):
        print("upload folder %s ======> %s" % (localFolder, remoteFolder))
        localFolderFiles = list(getLocalFolderFiles(localFolder))
        for ind, localFile in enumerate(localFolderFiles, start=1):
            basename = os.path.basename(localFolder)
            filename = os.path.split(localFile)[-1]
            targetFolder = remoteFolder + "/" + basename + "/" + \
                           standardizePath(os.path.dirname(localFile.replace(localFolder, "")))
            if not os.path.exists(targetFolder):
                self.mkdirTree(targetFolder)
            targetFile = standardizePath(os.path.join(targetFolder, filename))
            print("\tupload %s ======> %s uploading %d/%d" % (localFile, targetFile, ind, len(localFolderFiles)))
            self.upload(localFile, targetFile)

        print("upload folder %s ======> %s Done!" % (localFolder, remoteFolder))

    def download(self, remotePath, localPath):
        self.sFTPClient.get(remotePath, localPath, callback=callback)

    def downloadFolder(self, remoteFolder, localFolder):

        print("download folder %s ======> %s" % (remoteFolder, localFolder))
        remote_folder_files = self.getFolderFiles(remoteFolder)
        for ind, remote_file in enumerate(remote_folder_files, start=1):
            local_folder, _ = os.path.split(remote_file)
            if not os.path.exists(local_folder):
                os.makedirs(local_folder)
            print("\t%s======>%s %d/%d" % (remote_file, remote_file, ind, len(remote_folder_files)))
            self.download(remote_file, remote_file)
        if remoteFolder != localFolder:
            shutil.move(remoteFolder, localFolder)
        print("download folder %s ======> %s Done!" % (remoteFolder, localFolder))

    def rename(self, oldPath, newPath):

        self.sFTPClient.rename(oldPath, newPath)

    def chmod(self, path, mode=0o755):
        self.sFTPClient.chmod(path, mode)

    def mkdir(self, path, mode=0o755):
        self.sFTPClient.mkdir(path, mode=mode)
        return self.exists(path)

    def mkdirTree(self, path, mode=0o755):
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

    def rmTree(self, path):
        self.exec_command("rm -rf %s" % path)

    def chdir(self, path):
        self.sFTPClient.chdir(path)

    def symlink(self, source, dest):
        self.sFTPClient.symlink(source, dest)

    def unlink(self, linkname):
        self.remove(linkname)

    def open(self, filename, mode="r", bufferSize=-1):

        return self.sFTPClient.open(filename, mode, bufferSize)

    def chown(self, path, uid, gid):
        return self.sFTPClient.chown(path, uid, gid)

    def listdir(self, path="."):

        return self.sFTPClient.listdir(path)

    def getFolderFiles(self, folder):
        result_list = []

        def get_file(folderName):
            for base_path in self.listdir(folderName):
                abs_path = standardizePath(os.path.join(folderName, base_path))
                if self.isdir(abs_path):
                    get_file(abs_path)
                elif self.isfile(abs_path):
                    result_list.append(abs_path)
                elif self.islink(abs_path):
                    result_list.append(abs_path)

        get_file(folder)
        return result_list

    def stat(self, path):

        return self.sFTPClient.stat(path)

    def lstat(self, path):

        return self.sFTPClient.lstat(path)

    def exists(self, path):
        try:
            self.stat(path)
        except OSError:
            return False
        return True

    def isfile(self, path):
        try:
            st = self.stat(path)
        except OSError:
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
        except OSError:
            return False
        return stat.S_ISDIR(st.st_mode)

    @staticmethod
    def ismount(path):

        def _get_bothseps(p):
            if isinstance(p, bytes):
                return b'\\/'
            else:
                return '\\/'

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
