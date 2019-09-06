#!/usr/bin/python
# -*- coding: utf-8 -*-

import threading

import wx
from pubsub import pub

from handler import main_process
from logger import LOG
from tools import *

# 根据当前文件获取当前路径
# CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))


class WorkerThread(threading.Thread):
    def __init__(self, url: str, numbers: int, visual: bool, logger=None):
        super().__init__()
        self.url = url
        self.numbers = numbers
        self.visual = visual
        self.logger = logger
        self.start()

    def run(self):
        pub.sendMessage('update', msg='start')
        main_process(url=self.url, numbers=self.numbers, visual=self.visual, logger=self.logger)
        pub.sendMessage('update', msg='finish')

    def stop(self):
        try:
            async_raise(self.ident, SystemExit)
        except (ValueError, SystemError):
            self.logger.exception("停止线程时遇到异常: ")
            pass


class ProcessOnFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super(ProcessOnFrame, self).__init__(*args, **kw)
        # 绑定关闭事件
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.icon = get_resource_file(relative_path='favicon.ico', reference=__file__)
        self.logger = None
        self.worker = None
        self.tc_link, self.ch_number, self.tc_log, self.ck_visualization, self.btn_signup = None, None, None, None, None
        self.initUI()
        self.Center()
        self.Show()

    def onClose(self, event):
        if self.worker and self.worker.is_alive():
            ret = wx.MessageBox(u'程序正在运行中，是否关闭程序？', u'确认退出', wx.OK | wx.CANCEL)
            if ret == wx.OK:
                if self.worker.is_alive():
                    self.worker.stop()
                event.Skip()
        else:
            ret = wx.MessageBox(u'是否关闭程序？',  u'确认退出', wx.OK | wx.CANCEL)
            if ret == wx.OK:
                event.Skip()

    def initUI(self):
        # 设置窗口图标
        self.SetIcon(wx.Icon(self.icon, wx.BITMAP_TYPE_ICO))

        panel = wx.Panel(self)

        # 邀请链接/邀请用户数标签
        st_link = wx.StaticText(panel, label=u'邀请链接： ', style=wx.TE_LEFT)
        st_desc_link = wx.StaticText(panel, label=u'注：在账户中心最下方可以找到邀请链接，'
                                                  u'如：https://www.processon.com/i/5cc564f5e4b09eb4ac2b498e',
                                     style=wx.TE_LEFT | wx.ST_ELLIPSIZE_END)
        st_number = wx.StaticText(panel, label=u'邀请用户数： ', style=wx.TE_LEFT)
        st_desc_number = wx.StaticText(panel, label=u'注：每个用户通过邀请链接注册成功后，你会获得3张文件数量的奖励')
        # 邀请链接输入框
        self.tc_link = wx.TextCtrl(panel, style=wx.TE_LEFT)
        # 邀请用户数选择器
        choices = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
        self.ch_number = wx.Choice(panel, choices=choices)
        self.ch_number.SetSelection(0)
        # self.Bind(wx.EVT_CHOICE, self.onChoice, self.ch_number)
        # 日志
        self.tc_log = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        # 可视化勾选框
        self.ck_visualization = wx.CheckBox(panel, label=u'可视化', style=wx.CHK_2STATE)
        # 邀请注册按钮
        self.btn_signup = wx.Button(panel, label=u'邀请注册')
        self.Bind(wx.EVT_BUTTON, self.onSignUpClick, self.btn_signup)

        # 邀请链接组件布局
        bs_link = wx.BoxSizer(wx.HORIZONTAL)
        bs_link.Add(st_link, proportion=0, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT, border=5)
        bs_link.Add(self.tc_link, proportion=2, flag=wx.ALL | wx.EXPAND, border=5)

        bs_desc_link = wx.BoxSizer(wx.HORIZONTAL)
        bs_desc_link.Add(st_desc_link, proportion=0, flag=wx.LEFT | wx.RIGHT | wx.ALIGN_LEFT, border=5)

        # 邀请用户数组件布局
        bs_number = wx.BoxSizer(wx.HORIZONTAL)
        bs_number.Add(st_number, proportion=0, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT, border=5)
        bs_number.Add(self.ch_number, proportion=0, flag=wx.ALL, border=5)
        bs_number.Add(st_desc_number, proportion=0, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)

        # 日志组件布局
        bs_log = wx.BoxSizer(wx.HORIZONTAL)
        bs_log.Add(self.tc_log, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)

        # 邀请注册按钮组件布局
        bs_signup = wx.BoxSizer(wx.HORIZONTAL)
        bs_signup.AddStretchSpacer(1)
        bs_signup.Add(self.ck_visualization, proportion=0, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        bs_signup.Add(self.btn_signup, proportion=0, flag=wx.ALL, border=5)

        bs_all = wx.BoxSizer(wx.VERTICAL)
        bs_all.Add(bs_link, proportion=0, flag=wx.TOP | wx.LEFT | wx.RIGHT | wx.EXPAND, border=5)
        bs_all.Add(bs_desc_link, proportion=0, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, border=5)
        bs_all.Add(bs_number, proportion=0, flag=wx.ALL | wx.EXPAND, border=5)
        bs_all.Add(bs_log, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        bs_all.Add(bs_signup, proportion=0, flag=wx.ALL | wx.EXPAND, border=5)
        panel.SetSizer(bs_all)
        self.logger = LOG(name=__name__, topic='log').getLogger()
        # 订阅消息队列
        pub.subscribe(self.updateButtonStatus, 'update')
        pub.subscribe(self.updateLogMessage, 'log')

    def onSignUpClick(self, event):
        self.worker = WorkerThread(url=self.tc_link.GetValue(), numbers=int(self.ch_number.GetStringSelection()),
                                   visual=self.ck_visualization.GetValue(), logger=self.logger)
        event.GetEventObject().Disable()
        self.ck_visualization.Disable()

    def updateButtonStatus(self, msg):
        if msg == 'start':
            self.tc_log.AppendText(u'========== 邀请注册开始 ==========\n')
        elif msg == 'finish':
            self.tc_log.AppendText(u'========== 邀请注册完成 ==========\n\n')
            self.worker = None
            self.ck_visualization.Enable()
            self.btn_signup.Enable()

    def updateLogMessage(self, msg):
        self.tc_log.AppendText(msg)


if __name__ == '__main__':
    app = wx.App()
    ProcessOnFrame(None, title='ProcessOn邀请用户注册, 增加个人文件数', size=(600, 400))
    app.MainLoop()
    sys.exit(0)
