#!/usr/bin/python
# -*- coding: utf-8 -*-

import hashlib
import logging
import random
import re
import requests
import string
import time

from bs4 import BeautifulSoup

# 日志句柄
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(module)s - %(threadName)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)


class TempMailApi(object):
    def __init__(self, proxy: str = '', logger: logging.Logger = None):
        if logger:
            global LOGGER
            LOGGER = logger
        self.proxy = proxy
        self.username = ''
        self.domain = ''
        self.email = ''
        self.email_md5 = ''
        self.domains = []
        self.session = requests.Session()
        self.proxies = {}
        if proxy:
            self.proxies.update({'https' if proxy.startswith('https') else 'http': proxy})
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/76.0.3809.100 Safari/537.36'
        }
        requests.packages.urllib3.disable_warnings()
        self.generate_mailbox()

    def get_domains(self):
        # noinspection PyBroadException
        try:
            url = r'https://api4.temp-mail.org/request/domains/format/json'
            res = self.session.get(url, headers=self.headers, proxies=self.proxies, verify=False, timeout=5)
            if res.status_code != requests.codes.ok:
                LOGGER.error("访问地址[%s], 返回的响应状态码为: %d" % (url, int(res.status_code)))
                self.domains = []
            else:
                self.domains = res.json()
        except Exception:
            LOGGER.exception("获取邮箱域名列表时遇到异常: ")
            self.domains = []

    # 随机生成用户名
    def generate_username(self, length: int = 8):
        # 随机生成字母数字组成的指定长度字符串
        self.username = ''.join(random.sample(string.ascii_letters + string.digits, length))

    # 生成临时邮箱
    def generate_mailbox(self):
        if not self.domain:
            if not self.domains:
                self.get_domains()
            self.domain = random.choice(self.domains)
        if not self.username:
            self.generate_username()
        self.email = "%s%s" % (str(self.username).lower(), self.domain)
        self.email_md5 = hashlib.new('md5', str(self.email).encode(encoding='utf-8')).hexdigest()

    def get_mail(self, sender=None, subject=None):
        """
        获取邮件
        :param sender: 发件人
        :param subject: 邮件主题
        :return: TempMail邮件对象字典, 参数如下:
        Response parameters:
        Name	            Description
        mail_unique_id      Unique identifier assigned by the system.
        mail_id             Unique identifier of the message in md5 hash assigned by the system.
        mail_address_id     md5 email address hash
        mail_from           Sender
        mail_subject	    Subject
        mail_preview	    Preview
        mail_text_only	    Message in text or html format (main)
        mail_text	        Message only in text format
        mail_html	        Message only in html format
        """
        mail = None
        # noinspection PyBroadException
        try:
            start = time.time()
            url = r'https://api4.temp-mail.org/request/mail/id/{}/format/json'.format(self.email_md5)
            # 60秒内循环刷新收件箱, 找到匹配的邮件则退出
            while time.time() - start < 60:
                time.sleep(1)
                # noinspection PyBroadException
                try:
                    res = self.session.get(url, headers=self.headers, proxies=self.proxies, verify=False, timeout=5)
                    if res.status_code != requests.codes.ok:
                        continue
                    mails = res.json()
                    if not mails:
                        continue
                    # 发件者 或 主题 非None时, 倒序遍历收件箱, 匹配到一个邮件则退出循环
                    elif sender or subject:
                        # 收件箱邮件顺序为: 新邮件在下面; 因此需要倒序遍历
                        for m in mails[::-1]:
                            m_from = str(m['mail_from'])
                            m_subject = str(m['mail_subject'])
                            if sender and subject and -1 != m_from.find(sender) and m_subject == subject:
                                mail = m
                                break
                            elif sender and -1 != m_from.find(sender):
                                mail = m
                                break
                            elif subject and m_subject == subject:
                                mail = m
                                break
                    else:
                        mail = mails[-1]
                        break
                    if mail is None:
                        continue
                    else:
                        break
                except Exception:
                    continue
            if not mail:
                LOGGER.error("等待60秒后仍未收到目标邮件!")
        except Exception:
            LOGGER.exception("获取邮件时遇到异常: ")
        finally:
            return mail

    def get_mail_content(self, sender=None, subject=None, is_delete=False):
        """
        获取邮件内容
        :param sender: 发件人
        :param subject: 邮件主题
        :param is_delete: 是否删除该邮件
        :return: 匹配的邮件内容
        """
        # noinspection PyBroadException
        try:
            mail = self.get_mail(sender=sender, subject=subject)
            if not mail:
                LOGGER.error("获取邮件失败!")
                return ''
            if is_delete:
                # noinspection PyBroadException
                try:
                    self.delete_mail(mail['mail_id'])
                except Exception:
                    pass
            return str(mail['mail_text_only'])
        except Exception:
            LOGGER.exception("获取邮件内容时遇到异常: ")
            return ''

    # 删除邮件
    def delete_mail(self, mail_id):
        # noinspection PyBroadException
        try:
            if mail_id:
                url = r'https://api4.temp-mail.org/request/delete/id/{}/format/json'.format(mail_id)
                res = self.session.get(url, headers=self.headers, proxies=self.proxies, verify=False, timeout=5)
                if res.status_code != requests.codes.ok:
                    LOGGER.error("访问地址[%s], 返回的响应状态码为: %d" % (url, int(res.status_code)))
                    return False
                if 'success' == str(res.json()['result']).lower():
                    return True
                else:
                    LOGGER.error("删除邮件返回结果为: %s" % res.text)
                    return False
        except Exception:
            LOGGER.exception("删除邮件时遇到异常: ")
            return False

    # 删除邮箱
    def delete_mailbox(self):
        # noinspection PyBroadException
        try:
            if self.email and self.email_md5:
                url = r'https://api4.temp-mail.org/request/delete_address/id/{}/format/json'.format(self.email_md5)
                res = self.session.get(url, headers=self.headers, proxies=self.proxies, verify=False, timeout=5)
                if res.status_code != requests.codes.ok:
                    LOGGER.error("访问地址[%s], 返回的响应状态码为: %d" % (url, int(res.status_code)))
                    return False
                if 'success' == str(res.json()['result']).lower():
                    self.email = ''
                    self.email_md5 = ''
                    return True
                else:
                    LOGGER.error("删除邮箱返回结果为: %s" % res.text)
                    return False
        except Exception:
            LOGGER.exception("删除邮箱时遇到异常: ")
            return False


if __name__ == '__main__':
    # with open(r'E:\Workspace\test\test.html', mode='r', encoding='utf-8') as f:
    #     html_text = BeautifulSoup(f, 'html.parser')
    # code = html_text.find('div', attrs={'class', 'mailcontentbox'}).find('strong', text=re.compile('\\d+')).get_text()
    # print(code)
    exit(0)
