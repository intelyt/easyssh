# coding:utf-8
from typing import NoReturn, List, Any
import os
import stat

try:
    from nt import _getvolumepathname
except ImportError:
    _getvolumepathname = None

from paramiko import Transport, SFTPClient, SSHClient, SFTPFile
import paramiko

win = "win"

winsep = "\\"
unixsep = "/"


def get_local_folder_files(folder: str) -> List[str]:
    """
    递归获取本地文件夹所有的文件
    :param folder:
    :return:
    """
    result_list: List = []

    def get_file(folderName):
        for f in os.listdir(folderName):
            f = os.path.join(folderName, f)
            if os.path.isdir(f):
                get_file(f)
            elif os.path.isfile(f):
                result_list.append(f)
            elif os.path.islink(f):
                result_list.append(f)
    get_file(folder)
    return result_list


def to_str(bytes_or_str):
    """
    transfer bytes to utf8 str if param is bytes
     else do nothing
    :param bytes_or_str:
    :return:
    """
    return bytes_or_str.decode('utf-8') if isinstance(bytes_or_str, bytes) else bytes_or_str


class SSHConnection(object):
 
    def __init__(self, **kwargs):
        """
        to operate an linux server like in your computer
        Now only python3 is supported
        :param kwargs:
                    host -> str:  an ipv4 address
                    port -> int: default is 22
                    username -> str: ssh login username
                    password -> str: ssh login password (password or hostkey is necessary)
                    hostkey -> str: ssh login private key (password or hostkey is necessary)
        """

        self._transport: Transport = None
        self._ssh: SSHClient = None
        self._sftp: SFTPClient = None

        self._host: str = kwargs["host"]
        self._port: int = kwargs["port"] if kwargs["port"] else 22
        self._hostkey: str = kwargs["hostkey"] if kwargs["hostkey"] else None
        self._username: str = kwargs["username"]
        self._password: str = kwargs["password"] if kwargs["password"] else None

    @property
    def platform(self) -> str:
        from sys import platform
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

    def connect(self) -> NoReturn:
        """
        connect to the server
        :return:
        """
        # 创建 管道
        transport: Transport = paramiko.Transport(self.host, self.port)
        if self.password:
            transport.connect(username=self.username, password=self.password)
        else:
            privateKey = paramiko.RSAKey.from_private_key_file(self.hostkey)
            transport.connect(username=self.username, pkey=privateKey)
        self._transport = transport
        # 利用创建ssh 连接
        ssh: SSHClient = paramiko.SSHClient()
        ssh._transport = self._transport
        self._ssh = ssh

        # 利用 创建sftp客户端
        sftp: SFTPClient = paramiko.SFTPClient.from_transport(self._transport)
        self._sftp = sftp

    def disconnect(self) -> NoReturn:
        """
        disconnect to the server
        :return:
        """
        self.sshClient.close()
        self.transport.close()
        self.sFTPClient.close()

    def exec_command(self, command: str, timeout=3600) -> str:
        """
        maybe function system is better to understand
        Execute a command on the SSH server.  A new `.Channel` is opened and
        the requested command is executed.  The command's input and output
        streams are returned as Python ``file``-like objects representing
        stdin, stdout, and stderr.
        :param str command: the command to execute
        :param int timeout: command timout
       """
        stdin, stdout, stderr = self.sshClient.exec_command(command, timeout=timeout)
        res = to_str(stdout.read())
        error = to_str(stderr.read())
        return error if error.strip() else res

    def system(self, command: str, timeout=3600) -> str:
        """
        Execute a command on the SSH server.  A new `.Channel` is opened and
        the requested command is executed.  The command's input and output
        streams are returned as Python ``file``-like objects representing
        stdin, stdout, and stderr.
        :param str command: the command to execute
        :param int timeout: command timout
       """
        stdin, stdout, stderr = self.sshClient.exec_command(command, timeout=timeout)
        res = to_str(stdout.read())
        error = to_str(stderr.read())
        return error if error.strip() else res

    def upload(self, localpath: str, remotepath: str, mode=0o755) -> NoReturn:
        """
        Copy a local file (``localpath``) to the SFTP server as ``remotepath``.
        Any exception raised by operations will be passed through.  This
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
         """
        foldername, filepath = os.path.split(remotepath)
        if not self.exists(foldername):
            self.system("mkdir -p %s" % foldername)
        self.sFTPClient.put(localpath, remotepath)
        if mode:
            self.sFTPClient.chmod(remotepath, mode)

    def upload_folder(self, localfolder: str, remotefolder: str):
        """
          upload local folder to remote folder
         :param localfolder:
         :param remotefolder:
         :return:
        """
        local_folder_files = get_local_folder_files(localfolder)
        for local_file in local_folder_files:
            remote_file = local_file.replace(localfolder, remotefolder, 1)
            if self.platform.startswith(win):
                remote_file = remote_file.replace(winsep, unixsep)
            self.upload(local_file, remote_file)

    def download(self, remotepath: str, localpath: str) -> NoReturn:
        """
        Copy a remote file (``remotepath``) from the SFTP server to the local
        host as ``localpath``.  Any exception raised by operations will be
        passed through.  This method is primarily provided as a convenience.
        :param str remotepath: the remote file to copy
        :param str localpath: the destination path on the local host

        """
        self.sFTPClient.get(remotepath, localpath)

    def download_folder(self, remotefolder: str, localfolder: str):
        """

        :param remotefolder:
        :param localfolder:
        :return:
        """
        remote_folder_files = self.get_folder_files(remotefolder)
        for remote_file in remote_folder_files:
            local_file = remote_file.replace(localfolder, remotefolder, 1)
            if self.platform.startswith(win):
                local_file = local_file.replace(unixsep, winsep)
            self.upload(local_file, remote_file)

    def rename(self, oldpath: str, newpath: str) -> NoReturn:
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

    def chmod(self, path: str, mode=0o755) -> NoReturn:
        """
        Change the mode (permissions) of a file.  The permissions are
        unix-style and identical to those used by Python's `os.chmod`
        function.

       :param str path: path of the file to change the permissions of
       :param int mode: new permissions
       """
        self.sFTPClient.chmod(path, mode)

    def mkdir(self,  path: str, mode=0o755) -> NoReturn:
        """
        Create a folder (directory) named ``path`` with numeric mode ``mode``.
        The default mode is 0777 (octal).  On some systems, mode is ignored.
        Where it is used, the current umask value is first masked out.

        :param str path: name of the folder to create
        :param int mode: permissions (posix-style) for the newly-created folder default is 775
       """
        self.sFTPClient.mkdir(path, mode=mode)

    def mkdir_p(self, path: str, mode=0o755) -> NoReturn:
        """
        linux is mkdir -p path & chmod path mode
        Create a folder (directory) named ``path`` with numeric mode ``mode``.
        The default mode is 0777 (octal).  On some systems, mode is ignored.
        Where it is used, the current umask value is first masked out.
        :param str path: name of the folder to create
        :param int mode: permissions (posix-style) for the newly-created folder default is 775

        """
        self.exec_command("mkdir -p %s" % path)
        if mode:
            self.sFTPClient.chmod(path, mode)

    def remove(self, path: str) -> NoReturn:
        """
        Remove the file at the given path.  This only works on files; for
        removing folders (directories), use `rmdir`.

        :param str path: path (absolute or relative) of the file to remove
        :raises: ``IOError`` -- if the path refers to a folder (directory)
        """
        self.sFTPClient.remove(path)

    def rmdir(self, path: str) -> NoReturn:
        """
        Remove the folder named ``path``.
        :param str path: name of the folder to remove
        """
        self.sFTPClient.rmdir(path)

    def rmdir_rf(self, path: str) -> NoReturn:
        """
        linux is rm -rf path
        Remove the folder named ``path``.
        :param str path: name of the folder to remove
       """
        for file in self.get_folder_files(path):
            self.remove(file)
        rmdir_list = []

        def rmdir_p(folderName):
            for f in self.listdir(folderName):
                f = os.path.join(folderName, f).replace("\\", "/")
                if self.isdir(f):
                    rmdir_p(f)
                    rmdir_list.append(f)
        rmdir_p(path)
        for inner_folder in rmdir_list:
            self.rmdir(inner_folder)
        self.rmdir(path)

    def chdir(self, path: str) -> NoReturn:
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

    def symlink(self, source: str, dest: str) -> NoReturn:
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

    def open(self, filename: str, mode="r", bufsize=-1) -> SFTPFile:
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

    def normalize(self, path: str) -> str:
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

    def chown(self, path: str, uid: int, gid: int):
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

    def get_channel(self) -> object:
        """
        Return the underlying `.Channel` object for this SFTP session.  This
        might be useful for doing things like setting a timeout on the channel.
        """
        return self.sFTPClient.get_channel()

    def listdir(self, path=".") -> List[str]:
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

    def get_folder_files(self, folder: str) -> List[str]:
        """
        获取文件夹下所有的文件 类似 os.walk
        :return:
        """
        result_list: List = []

        def get_file(folderName):
            for f in self.listdir(folderName):
                f = os.path.join(folderName, f).replace("\\", "/")
                if self.isdir(f):
                    get_file(f)
                elif self.isfile(f):
                    result_list.append(f)
        get_file(folder)
        return result_list

    def stat(self, path: str) -> Any:
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

    def lstat(self, path: str) -> Any:
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
    def ismount(path: str):
        """Test whether a path is a mount point (a drive root, the root of a
        share, or a mounted volume)"""
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

    def getsize(self, filename: str) -> int:
        """Return the size of a file,
        reported by os.stat().
        :param str filename: the filename need to getsize in the remote server
        """
        return self.stat(filename).st_size

    def getcwd(self) -> str:
        """
        Return the "current working directory" for this SFTP session, as
        emulated by Paramiko.  If no directory has been set with `chdir`,
        this method will return ``None``.
        """
        return self.sFTPClient.getcwd()

    # --------------------------
    def download_from_svn(self, localPath: str, svnPath: str) -> NoReturn:
        """
        download file to the server from remote svn path
        :param localPath: the server local path
        :param svnPath: remote svn path
        :return:
        """
        if svnPath.startswith('http'):
            command = "wget --no-check-certificate -P '{localPath}' '{svnPath}' " \
                      " --http-user='atdeploy' --http-password='Pass2016'".format(localPath=localPath, svnPath=svnPath)
            self.exec_command(command)
        elif svnPath.startswith('ftp'):
            command = "wget  -r -P '{localPath}' '{svnPath}' -nH -nc -nd " \
                      "--ftp-user='cisysadmin'--ftp-password='Pass2016'".format(localPath=localPath, svnPath=svnPath)
            self.exec_command(command)
        else:
            print("error")









