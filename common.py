# -*- coding:utf-8 -*-
import os
import socket
import math
import sys
from typing import Iterator


win = "win"
win_sep = "\\"
unix_sep = "/"


def progressbar(current_bytes: int, total_bytes: int) -> None:
    percent = '{:.2%}'.format(current_bytes / total_bytes)
    rate_of_progress = "%dkb/%dkb" % (current_bytes, total_bytes)
    sys.stdout.write('\r')

    sys.stdout.write('\t\033[31m[%-50s] %s  %s \033[1m' % ('=' * int(math.floor(current_bytes * 50 / total_bytes)),
                                                           percent, rate_of_progress))
    sys.stdout.flush()
    if current_bytes == total_bytes:
        sys.stdout.write('\n')


def callback(current_bytes: int, total_bytes: int):
    progressbar(current_bytes, total_bytes)


def get_local_folder_files(folder: str) -> Iterator[str]:
    """
    递归获取本地文件夹所有的文件
    :param folder:
    :return: 生成器
    """
    for root, dirs, files in os.walk(folder, topdown=False):
        for name in files:
            yield os.path.join(root, name)


def to_str(bytes_or_str):
    """
    transfer bytes to utf8 str if param is bytes
     else do nothing
    :param bytes_or_str:
    :return:
    """
    return bytes_or_str.decode('utf-8') if isinstance(bytes_or_str, bytes) else bytes_or_str


def scan_by_socket(host: str, port: int):
    """
    to test host's port whether is open
    :param host:
    :param port:
    :return:
    """
    if not (0 < port < 65536):
        raise Exception("not standard ip")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as scan_socket:
        status_code = scan_socket.connect_ex((host, port))
        if status_code == 0:
            return True


__all__ = ["win", "win_sep", "unix_sep", "callback", "get_local_folder_files", "to_str", "scan_by_socket"]

