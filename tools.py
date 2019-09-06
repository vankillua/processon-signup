#!/usr/bin/python
# -*- coding: utf-8 -*-

import ctypes
import inspect
import os
import sys


def get_resource_path(relative_path: str):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath('.'))
    return os.path.join(base_path, relative_path)


def get_resource_file(relative_path: str, reference: str = '.'):
    current_path = os.path.abspath(os.path.dirname(reference))
    file_path = os.path.join(current_path, relative_path)
    if not os.path.isfile(file_path):
        """
        Get absolute path to resource, works for dev and for PyInstaller
        """
        base_path = getattr(sys, '_MEIPASS', current_path)
        file_path = os.path.join(base_path, relative_path)
        if not os.path.isfile(file_path):
            return ''
    return file_path


def async_raise(tid, ex_ctype):
    """
    raises the exception, performs cleanup if needed
    :param tid:
    :param ex_ctype:
    :return:
    """
    tid = ctypes.c_long(tid)
    if not inspect.isclass(ex_ctype):
        ex_ctype = type(ex_ctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(ex_ctype))
    if res == 0:
        raise ValueError("无效的线程ID[%d]!" % tid)
    elif res != 1:
        """
        if it returns a number greater than one, you're in trouble,
        and you should call it again with exc=NULL to revert the effect
        """
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc处理失败!")


if __name__ == '__main__':
    exit(0)
