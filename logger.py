#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import time
import wx

from pubsub import pub


class LOG(object):
    def __init__(self, name: str = None, text_ctrl: wx.TextCtrl = None, topic: str = ''):
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(module)s - %(threadName)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(name)
        if text_ctrl:
            self.logger.addHandler(WxTextCtrlHandler(text_ctrl))
        if topic:
            self.logger.addHandler(PubTopicMessageHandler(topic))

    def getLogger(self):
        return self.logger


class WxTextCtrlHandler(logging.Handler):
    def __init__(self, text_ctrl: wx.TextCtrl = None):
        logging.Handler.__init__(self)
        self.text_ctrl = text_ctrl

    def emit(self, record):
        if record.levelno < self.level:
            return
        time_str = time.strftime('%Y-%m-%d %H:%M:%S.%U')
        self.text_ctrl.AppendText("[%s] [%s] %s\n" % (time_str, record.levelname, record.getMessage()))


class PubTopicMessageHandler(logging.Handler):
    def __init__(self, topic: str):
        super().__init__()
        self.topic = topic

    def emit(self, record):
        if record.levelno < self.level:
            return
        message = "[%s] [%s] %s\n" % (time.strftime('%Y-%m-%d %H:%M:%S.%U'), record.levelname, record.getMessage())
        pub.sendMessage(self.topic, msg=message)


if __name__ == '__main__':
    exit(0)
