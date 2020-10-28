# -*- coding:utf-8 -*-
import warnings
import os
import stat
from sys import platform
from typing import List


try:
    from nt import _getvolumepathname
except ImportError:
    _getvolumepathname = None

import paramiko
from paramiko import Transport, SFTPClient, SSHClient

from .common import *


class SSHConnection:
    """
    For example:

    use username and password
    server = {"host": "ip", "port": 22, "username": "Btbtcore", "password": "Pass2020", "hostkey": "None"}
    ssh = SSHConnection(**server)
    ssh.connect()
    ssh.exec_command("pwd")
    ssh.disconnect()

    user private key

    server = {"host": "ip", "port": 22, "username": "Btbtcore", "password": None, "hostkey": "/tmp/atdeploy_rsa"}
    ssh = SSHConnection(**server)
    ssh.connect()
    ssh.exec_command("pwd")
    ssh.disconnect()

    """

    def __init__(self, **kwargs):
        """
        to operate an linux server like in your computer
        Now only python3 is supported
        :param kwargs:
                    host -> str:  an ipv4 address default is 127.0.0.1
                    port -> int: default is 22
                    username -> str: ssh login username default is root
                    password -> str: ssh login password (password or hostkey is necessary)
                    hostkey -> str: ssh login private key (password or hostkey is necessary)
                    compress -> bool: whether to use compression mode default is False
                    timeout -> int:
        """

        self._transport = None
        self._ssh = None
        self._sftp = None

        self._host = kwargs.get("host", "127.0.0.1")
        self._port = kwargs.get("port", 22)
        self._username = kwargs.get("username", "root")
        self._password = kwargs.get("password", None)
        self._hostkey = kwargs.get("hostkey", None)
        self._compress = kwargs.get("compress", False)
        self._auth_timeout = kwargs.get("auth_timeout", None)
        self._timeout = kwargs.get("timeout", None)

    @property
    def platform(self) -> str:
        return platform

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def hostkey(self) -> str:
        return self._hostkey

    @property
    def username(self) -> str:
        return self._username

    @property
    def password(self) -> str:
        return self._password

    @property
    def sshClient(self) -> SSHClient:
        return self._ssh

    @property
    def transport(self) -> Transport:
        return self._transport

    @property
    def sFTPClient(self) -> SFTPClient:
        return self._sftp

    def connect(self) -> None:
        """
        connect to the server
        :return:
        """
        # 先检测ip的端口是否通
        assert scan_by_socket(self.host, self.port)
        # 创建 管道
        transport = paramiko.Transport(self.host, self.port)
        # 设置登陆验证超时时间
        if self._auth_timeout:
            transport.auth_timeout = self._auth_timeout

        # 设置操作超时时间
        if self._timeout:
            transport.sock.settimeout(self._timeout)
        # 启数据压缩
        if self._compress:
            transport.use_compression()
        # 使用密码验证
        if self.password:
            transport.connect(username=self.username, password=self.password)
        else:
            # 使用私钥验证
            privateKey = paramiko.RSAKey.from_private_key_file(self.hostkey)
            transport.connect(username=self.username, pkey=privateKey)
        self._transport = transport
        # 利用创建ssh 连接
        ssh = paramiko.SSHClient()
        ssh._transport = self._transport
        self._ssh = ssh

        # 利用 创建sftp客户端(主要用来文件处理)
        sftp = paramiko.SFTPClient.from_transport(self._transport)
        self._sftp = sftp

    def disconnect(self) -> None:
        """
        disconnect to the server
        :return:
        """
        self.sshClient.close()
        self.transport.close()
        self.sFTPClient.close()

    def exec_command(self,
                     command,
                     bufsize=-1,
                     timeout=3600,
                     environment=None,
                     ) -> str:
        """

        :param command:
        :param bufsize:
        :param timeout:
        :param environment:
        :return:
        """

        stdin, stdout, stderr = self.sshClient.exec_command(command,
                                                            bufsize=bufsize,
                                                            timeout=timeout,
                                                            environment=environment)
        res = to_str(stdout.read())
        error = to_str(stderr.read())
        return error if error.strip() else res

    def upload(self, localpath: str, remotepath: str, mode=0o755, confirm=True) -> None:
        """
        Copy a local file (``localpath``) to the SFTP server as ``remotepath``.
         exception raised by operations will be passed through.  This
        method is primarily provided as a convenience. if mode will chmod remotepath mode

        The SFTP operations use pipelining for speed.

        :param str localpath: the local file to copy
        :param str remotepath: the destination path on the SFTP server. Note
         that the filename should be included. Only specifying a directory
         may result in an error.
         whether to do a stat() on the file afterwards to confirm the file
         size
        :param  mode =0o755
         :return: an `.SFTPAttributes` object containing attributes about the
         given file
        :param bool confirm:
        whether to do a stat() on the file afterwards to confirm the file
        size
         """
        if not os.path.isabs(localpath):
            localpath = os.path.join(os.getcwd(), localpath)

        foldername, filepath = os.path.split(remotepath)
        if not self.exists(foldername):
            self.makedirs(foldername)
        self.sFTPClient.put(localpath, remotepath, callback=callback, confirm=confirm)
        if mode:
            self.sFTPClient.chmod(remotepath, mode)

    def upload_folder(self, localfolder: str, remotefolder: str) -> None:
        """
          upload local folder to remote folder
         :param localfolder:
         :param remotefolder:
         :return:
        """
        if os.path.exists(remotefolder):
            warnings.warn('remote folder %s already exists please remove !' % remotefolder,
                          UserWarning)
        else:
            self.makedirs(remotefolder)

        if not os.path.isabs(localfolder):
            localfolder = os.path.join(os.getcwd(), localfolder)

        local_folder_files = list(get_local_folder_files(localfolder))
        print("upload folder %s ======> %s" % (localfolder, remotefolder))
        for index, local_file in enumerate(local_folder_files, start=1):

            remote_file = local_file.replace(localfolder, remotefolder, 1)

            if self.platform.startswith(win):
                remote_file = remote_file.replace(win_sep, unix_sep)
            print("\tupload %s ======> %s uploading %d/%d" % (local_file, remote_file, index, len(local_folder_files)))
            self.upload(local_file, remote_file)
        print("upload folder %s ======> %s Done!" % (localfolder, remotefolder))

    def download(self, remotepath: str, localpath: str) -> None:
        """
        Copy a remote file (``remotepath``) from the SFTP server to the local
        host as ``localpath``.   exception raised by operations will be
        passed through.  This method is primarily provided as a convenience.
        :param str remotepath: the remote file to copy
        :param str localpath: the destination path on the local host

        """
        if not os.path.isabs(localpath):
            localpath = os.path.join(os.getcwd(), localpath)

        foldername, filepath = os.path.split(localpath)
        if not os.path.exists(foldername):
            os.makedirs(foldername)

        self.sFTPClient.get(remotepath, localpath, callback=callback)

    def download_folder(self, remotefolder: str, localfolder: str) -> None:
        """

        :param remotefolder:
        :param localfolder:
        :return:
        """
        assert self.exists(remotefolder)

        if not os.path.isabs(localfolder):
            localfolder = os.path.join(os.getcwd(), localfolder)

        if os.path.exists(localfolder):
            warnings.warn('local folder %s already exists please remove !' % localfolder,
                          UserWarning)

        remote_folder_files = list(self.get_folder_files(remotefolder))

        print("download folder %s ======> %s" % (remotefolder, localfolder))
        for index, remote_file in enumerate(remote_folder_files, start=1):
            local_file = remote_file.replace(remotefolder, localfolder, 1)
            if self.platform.startswith(win):
                local_file = local_file.replace(unix_sep, win_sep)
            print("\t%s======>%s %d/%d" % (remote_file, local_file, index, len(remote_folder_files)))
            head, tail = os.path.split(local_file)
            if not os.path.exists(head):
                os.makedirs(head)
            self.download(remote_file, local_file)
        print("download folder %s ======> %s Done!" % (remotefolder, localfolder))

    def rename(self, oldpath: str, newpath: str) -> None:
        """
        Rename a file or folder from ``oldpath`` to ``newpath``.
       .. note::
           This method implements 'standard' SFTP ``RENAME`` behavior; those
           seeking the OpenSSH "POSIX rename" extension behavior should use
           `posix_rename`.
       :param str oldpath:
           existing name of the file or folder
       :param str newpath:
           new name for the file or folder, must not exist already
       :raises:
           ``IOError`` -- if ``newpath`` is a folder, or something else goes
           wrong
       """
        self.sFTPClient.rename(oldpath, newpath)

    def chmod(self, path: str, mode=0o755) -> None:
        """
        Change the mode (permissions) of a file.  The permissions are
        unix-style and identical to those used by Python's `os.chmod`
        function.

       :param str path: path of the file to change the permissions of
       :param int mode: new permissions
       """
        self.sFTPClient.chmod(path, mode)

    def mkdir(self, path: str, mode=0o755):
        """
        Create a folder (directory) named ``path`` with numeric mode ``mode``.
        The default mode is 0777 (octal).  On some systems, mode is ignored.
        Where it is used, the current umask value is first masked out.

        :param str path: name of the folder to create
        :param int mode: permissions (posix-style) for the newly-created folder default is 775
       """
        self.sFTPClient.mkdir(path, mode=mode)

    def makedirs(self, path: str, mode=0o755):
        """
        linux is mkdir -p path & chmod path mode
        Create a folder (directory) named ``path`` with numeric mode ``mode``.
        The default mode is 0777 (octal).  On some systems, mode is ignored.
        Where it is used, the current umask value is first masked out.
        :param str path: name of the folder to create
        :param int mode: permissions (posix-style) for the newly-created folder default is 775

        """
        if not self.exists(path):
            self.exec_command("mkdir -p %s" % path)
        if mode:
            self.sFTPClient.chmod(path, mode)

    def remove(self, path: str):
        """
        Remove the file at the given path.  This only works on files; for
        removing folders (directories), use `rmdir`.

        :param str path: path (absolute or relative) of the file to remove
        :raises: ``IOError`` -- if the path refers to a folder (directory)
        """
        if self.exists(path):
            self.sFTPClient.remove(path)

    def rmdir(self, path: str):
        """
        Remove the folder named ``path``.
        :param str path: name of the folder to remove
        """
        if self.exists(path):
            self.sFTPClient.rmdir(path)

    def rmtree(self, path: str):
        """
        linux is rm -rf path
        Remove the folder named ``path``.
        :param str path: name of the folder to remove
       """
        self.exec_command("rm -rf %s" % path)
        # for file in self.get_folder_files(path):
        #     self.remove(file)
        # rmdir_list = []
        #
        # def rmdir_p(folderName):
        #     for f in self.listdir(folderName):
        #         f = os.path.join(folderName, f).replace(win_sep, unix_sep)
        #         if self.isdir(f):
        #             rmdir_p(f)
        #             rmdir_list.append(f)
        #
        # rmdir_p(path)
        # for inner_folder in rmdir_list:
        #     self.rmdir(inner_folder)
        # self.rmdir(path)

    def chdir(self, path: str):
        """
        Change the "current directory" of this SFTP session.  Since SFTP
        doesn't really have the concept of a current working directory, this is
        emulated by Paramiko.  Once you use this method to set a working
        directory, all operations on this `.SFTPClient` object will be relative
        to that path. You can pass in ``None`` to stop using a current working
        directory.
        :param str path: new current working directory
        :raises:
            ``IOError`` -- if the requested path doesn't exist on the server
        """
        self.sFTPClient.chdir(path)

    def symlink(self, source: str, dest: str):
        """
        Create a symbolic link to the ``source`` path at ``destination``.

        :param str source: path of the original file
        :param str dest: path of the newly created symlink

        """
        self.sFTPClient.symlink(source, dest)

    def unlink(self, linkname: str):
        """
        Remove a file (same as remove()).
        If dir_fd is not None, it should be a file descriptor open to a directory,
        and path should be relative; path will then be relative to that directory.
        dir_fd may not be implemented on your platform.
        If it is unavailable, using it will raise a NotImplementedError.
        """
        self.remove(linkname)

    def open(self, filename, mode="r", bufsize=-1):
        """
        Open a file on the remote server.  The arguments are the same as for
        Python's built-in `python:file` (aka `python:open`).  A file-like
        object is returned, which closely mimics the behavior of a normal
        Python file object, including the ability to be used as a context
        manager.

        The mode indicates how the file is to be opened: ``'r'`` for reading,
        ``'w'`` for writing (truncating an existing file), ``'a'`` for
        appending, ``'r+'`` for reading/writing, ``'w+'`` for reading/writing
        (truncating an existing file), ``'a+'`` for reading/appending.  The
        Python ``'b'`` flag is ignored, since SSH treats all files as binary.
        The ``'U'`` flag is supported in a compatible way.

        Since 1.5.2, an ``'x'`` flag indicates that the operation should only
        succeed if the file was created and did not previously exist.  This has
        no direct mapping to Python's file flags, but is commonly known as the
        ``O_EXCL`` flag in posix.

        The file will be buffered in standard Python style by default, but
        can be altered with the ``bufsize`` parameter.  ``0`` turns off
        buffering, ``1`` uses line buffering, and any number greater than 1
        (``>1``) uses that specific buffer size.

        :param str filename: name of the file to open
        :param str mode: mode (Python-style) to open in
        :param int bufsize: desired buffering (-1 = default buffer size)
        :return: an `.SFTPFile` object representing the open file

        :raises: ``IOError`` -- if the file could not be opened.
        """

        return self.sFTPClient.open(filename, mode, bufsize)

    def normalize(self, path):
        """
           Return the normalized path (on the server) of a given path.  This
           can be used to quickly resolve symbolic links or determine what the
           server is considering to be the "current folder" (by passing ``'.'``
           as ``path``).

           :param str path: path to be normalized
           :return: normalized form of the given path (as a `str`)

           :raises: ``IOError`` -- if the path can't be resolved on the server
        """
        return self.sFTPClient.normalize(path)

    def chown(self, path, uid, gid):
        """
        Change the owner (``uid``) and group (``gid``) of a file.  As with
        Python's `os.chown` function, you must pass both arguments, so if you
        only want to change one, use `stat` first to retrieve the current
        owner and group.

        :param str path: path of the file to change the owner and group of
        :param int uid: new owner's uid
        :param int gid: new group id
        """
        return self.sFTPClient.chown(path, uid, gid)

    def get_channel(self):
        """
        Return the underlying `.Channel` object for this SFTP session.  This
        might be useful for doing things like setting a timeout on the channel.
        """
        return self.sFTPClient.get_channel()

    def listdir(self, path=".") -> List:
        """
        Return a list containing the names of the entries in the given
        ``path``.
        The list is in arbitrary order.  It does not include the special
        entries ``'.'`` and ``'..'`` even if they are present in the folder.
        This method is meant to mirror ``os.listdir`` as closely as possible.
        For a list of full `.SFTPAttributes` objects, see `listdir_attr`.

        :param str path: path to list (defaults to ``'.'``)
        """
        return self.sFTPClient.listdir(path)

    def get_folder_files(self, folder: str) -> List:
        """
        获取文件夹下所有的文件 类似 os.walk
        :return:
        """
        result_list = []

        def get_file(folderName):
            for base_path in self.listdir(folderName):
                abs_path = os.path.join(folderName, base_path).replace(win_sep, unix_sep)
                if self.isdir(abs_path):
                    get_file(abs_path)
                elif self.isfile(abs_path):
                    result_list.append(abs_path)
                elif self.islink(abs_path):
                    result_list.append(abs_path)

        get_file(folder)
        return result_list

    def stat(self, path: str):
        """
        Retrieve information about a file on the remote system.  The return
        value is an object whose attributes correspond to the attributes of
        Python's ``stat`` structure as returned by ``os.stat``, except that it
        contains fewer fields.  An SFTP server may return as much or as little
        info as it wants, so the results may vary from server to server.

        Unlike a Python `python:stat` object, the result may not be accessed as
        a tuple.  This is mostly due to the author's slack factor.

        The fields supported are: ``st_mode``, ``st_size``, ``st_uid``,
        ``st_gid``, ``st_atime``, and ``st_mtime``.

        :param str path: the filename to stat
        :return:
            an `.SFTPAttributes` object containing attributes about the given
            file
        """
        return self.sFTPClient.stat(path)

    def lstat(self, path: str):
        """
        Retrieve information about a file on the remote system, without
        following symbolic links (shortcuts).  This otherwise behaves exactly
        the same as `stat`.

        :param str path: the filename to stat
        :return:
          an `.SFTPAttributes` object containing attributes about the given
          file
        """
        return self.sFTPClient.lstat(path)

    def exists(self, path: str) -> bool:
        """Test whether a path exists.
          Returns False for broken symbolic links
         :param str path: the filename to test whether exists in the remote server
        """
        try:
            self.stat(path)
        except OSError:
            return False
        return True

    def isfile(self, path: str) -> bool:
        """Test whether a path is a regular
         file to test whether exists in the remote server
         :param str path: the filename to test whether if regular file in the remote server
         """
        try:
            st = self.stat(path)
        except OSError:
            return False
        return stat.S_ISREG(st.st_mode)

    def islink(self, path: str) -> bool:
        """
        Test whether a path is a symbolic link.
        This will always return false for Windows prior to 6.0.
        """
        try:
            st = self.lstat(path)
        except (OSError, AttributeError):
            return False
        return stat.S_ISLNK(st.st_mode)

    def isdir(self, path: str) -> bool:
        """Return true if the pathname
        refers to an existing directory.
        :param str path: the filename to test whether if is directory in the remote server

        """
        try:
            st = self.stat(path)
        except OSError:
            return False
        return stat.S_ISDIR(st.st_mode)

    @staticmethod
    def ismount(path: str) -> bool:
        """Test whether a path is a mount point (a drive root, the root of a
        share, or a mounted volume)"""

        return os.path.ismount(path)

    def get_st_size(self, filename: str):
        """Return the size of a file,
        reported by os.stat().
        :param str filename:
        """
        return self.stat(filename).st_size

    def get_st_mode(self, filename: str):
        """Return the mode of a file,
        reported by os.stat().
        :param str filename:
        """
        return self.stat(filename).st_mode

    def get_st_uid(self, filename: str):
        """Return the uid of a file,
        reported by os.stat().
        UserID
        :param str filename:
        """
        return self.stat(filename).st_mode

    def get_st_gid(self, filename: str):
        """Return the gid of a file,
        reported by os.stat().
        Group ID
        :param str filename:
        """
        return self.stat(filename).st_gid

    def get_st_atime(self, filename: str):
        """Return the atime of a file,
        reported by os.stat().
        最后一次访问文件或目录的时间 access time
        :param str filename:
        """
        return self.stat(filename).st_atime

    def get_st_mtime(self, filename: str):
        """Return the mtime of a file, modify time
        reported by os.stat().
        最后一次修改文件或目录的时间
        :param str filename:
        """
        return self.stat(filename).st_mtime

    def getcwd(self) -> str:
        """
        Return the "current working directory" for this SFTP session, as
        emulated by Paramiko.  If no directory has been set with `chdir`,
        this method will return ``None``.
        """
        result = self.sFTPClient.getcwd()
        return result






