# -*- coding:utf-8 -*-
import socket
from os import path, walk
from sys import stdout
from math import floor

import time


def progressbar(current_bytes, total_bytes):
    percent = '{:.2%}'.format(current_bytes / total_bytes)
    rate_of_progress = "%dkb/%dkb" % (current_bytes, total_bytes)
    stdout.write('\r')

    stdout.write('\t\033[31m[%-50s] %s  %s \033[1m' % ('=' * int(floor(current_bytes * 50 / total_bytes)),
                                                           percent, rate_of_progress))
    stdout.flush()
    if current_bytes == total_bytes:
        stdout.write('\n')


def callback(current_bytes, total_bytes):
    progressbar(current_bytes, total_bytes)


def getLocalFolderFiles(folder):

    for root, dirs, files in walk(folder, topdown=False):
        for name in files:
            yield path.join(root, name)


def toStr(bytes_or_str):

    return bytes_or_str.decode('utf-8') if isinstance(bytes_or_str, bytes) else bytes_or_str


def scanBySocket(host, port):

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as scan_socket:
        status_code = scan_socket.connect_ex((host, port))
        if status_code == 0:
            return True


def standardizePath(path):
    return path.replace("\\", "/")


def getStrftime(timestamp, format_string='%Y-%m-%d %H:%M:%S'):
    return time.strftime(format_string, time.localtime(timestamp))


__all__ = ["callback", "getLocalFolderFiles", "toStr", "scanBySocket", "standardizePath", "getStrftime"]






