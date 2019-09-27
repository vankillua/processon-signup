#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import random
import string
import time
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# 日志句柄
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(module)s - %(threadName)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)


class TempMail(object):
    # 临时邮箱网站
    WEB_URL = r'https://10minemail.com'
    WEB_URLS = {
        'change': urljoin(WEB_URL, r'/en/option/change/'),
        'refresh': urljoin(WEB_URL, r'/en/option/refresh/'),
        'delete': urljoin(WEB_URL, r'/en/option/delete/'),
        'view': urljoin(WEB_URL, r'/en/view'),
        'domains': r'https://api4.temp-mail.org/request/domains/format/json',
    }

    def __init__(self, proxy: str = '', auto: bool = False, logger: logging.Logger = None):
        if logger:
            global LOGGER
            LOGGER = logger
        self.proxy = proxy
        self.username = ''
        self.domain = ''
        self.email = ''
        self.domains = []
        self.csrf = ''
        self.session = requests.Session()
        self.proxies = {}
        if proxy:
            self.proxies.update({'https' if proxy.startswith('https') else 'http': proxy})
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/76.0.3809.100 Safari/537.36'
        }
        if auto:
            self.save_email()

    # 调用临时邮件网站的change接口
    def call_change_url(self, params=None):
        if params is None:
            params = {}
        # noinspection PyBroadException
        try:
            url = self.WEB_URLS['change']
            res = self.session.get(url, params=params, headers=self.headers, proxies=self.proxies)
            if res.status_code != requests.codes.ok:
                LOGGER.error("访问地址[%s], 返回的响应状态码为: %d" % (url, int(res.status_code)))
                return None
            return res
        except Exception:
            LOGGER.exception("调用change接口时遇到异常: ")
            return None

    # 获取csrf
    def get_csrf(self):
        # noinspection PyBroadException
        try:
            if not self.csrf:
                res = self.call_change_url()
                html = BeautifulSoup(res.text, 'html.parser')
                self.csrf = html.find('input', attrs={'name': 'csrf'}).get('value')
        except Exception:
            LOGGER.exception("获取csrf时遇到异常: ")
            self.csrf = ''

    # 从临时邮件网站获取邮箱域名列表
    def get_domains_old(self):
        # noinspection PyBroadException
        try:
            res = self.call_change_url()
            if not res:
                self.domains = []
            else:
                html = BeautifulSoup(res.text, 'html.parser')
                self.domains = [option.get('value') for option in html.find('select', id='domain').find_all('option')]
                if not self.csrf:
                    # noinspection PyBroadException
                    try:
                        self.csrf = html.find('input', attrs={'name': re.compile('csrf')}).get('value')
                    except Exception:
                        LOGGER.exception("从html中获取csrf时遇到异常: ")
                        self.csrf = ''
        except Exception:
            LOGGER.exception("获取邮箱域名列表时遇到异常: ")
            self.domains = []

    def get_domains(self):
        # noinspection PyBroadException
        try:
            url = self.WEB_URLS['domains']
            res = self.session.get(url, headers=self.headers, proxies=self.proxies)
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
    def generate_email(self):
        if not self.domain:
            if not self.domains:
                self.get_domains()
            self.domain = random.choice(self.domains)
        if not self.username:
            self.generate_username()
        self.email = "%s%s" % (str(self.username).lower(), self.domain)

    # 保存临时邮箱
    def save_email(self):
        # noinspection PyBroadException
        try:
            url = self.WEB_URLS['change']
            self.get_csrf()
            self.generate_email()
            data = {'csrf': self.csrf, 'mail': self.username, 'domain': self.domain}
            res = self.session.post(url, data=data, headers=self.headers, proxies=self.proxies)
            if res.status_code != requests.codes.ok:
                LOGGER.error("访问地址[%s], 返回的响应状态码为: %d" % (url, int(res.status_code)))
                return False
            return True
        except Exception:
            LOGGER.exception("保存临时邮箱[%s]时遇到异常: " % self.email)
            return False

    # 获取邮件
    def get_mail(self, sender=None, subject=None):
        href = ''
        # noinspection PyBroadException
        try:
            start = time.time()
            url = self.WEB_URLS['refresh']
            # 60秒内循环刷新收件箱, 找到匹配的邮件则退出
            while time.time() - start < 60:
                res = self.session.get(url, headers=self.headers, proxies=self.proxies)
                if res.status_code != requests.codes.ok:
                    continue
                html = BeautifulSoup(res.text, 'html.parser')
                try:
                    mails = html.find('div', attrs={'class': 'inbox-dataList'}).find('ul').find_all('li')
                except AttributeError:
                    continue
                mail = None
                if not mails:
                    continue
                # 发件者 或 主题 非None时, 倒序遍历收件箱, 匹配到一个邮件则退出循环
                elif sender or subject:
                    # 收件箱邮件顺序为: 新邮件在下面; 因此需要倒序遍历
                    for m in mails[::-1]:
                        try:
                            m_sender = m.find(attrs={'class': re.compile('inboxSenderName')}).get_text().strip()
                            m_subject = m.find(attrs={'class': re.compile('inboxSubject')}).get_text().strip()
                        except AttributeError:
                            continue
                        if sender and subject and sender == m_sender and subject == m_subject:
                            mail = m
                            break
                        elif sender and sender == m_sender:
                            mail = m
                            break
                        elif subject and subject == m_subject:
                            mail = m
                            break
                else:
                    mail = mails[-1]

                if mail is None:
                    continue
                # 提取邮件地址
                href = mail.find('a', href=re.compile(self.WEB_URLS['view'])).get('href')
                break
            if not href:
                LOGGER.error("等待60秒后仍未收到邮件!")
            else:
                LOGGER.debug("邮件地址为: %s" % href)
            return href
        except Exception:
            LOGGER.exception("获取邮件时遇到异常: ")
            return ''

    # 获取邮件内容
    def get_mail_content(self, sender=None, subject=None):
        # noinspection PyBroadException
        try:
            url = self.get_mail(sender, subject)
            if not url:
                LOGGER.error("获取邮件失败!")
                return ''
            res = self.session.get(url, headers=self.headers, proxies=self.proxies)
            if res.status_code != requests.codes.ok:
                LOGGER.error("访问地址[%s], 返回的响应状态码为: %d" % (url, int(res.status_code)))
            return res.text
        except Exception:
            LOGGER.exception("获取邮件内容时遇到异常: ")
            return ''

    # 删除临时邮箱
    def delete_email(self):
        # noinspection PyBroadException
        try:
            url = self.WEB_URLS['delete']
            params = {'_': int(time.time())}
            res = self.session.get(url, params=params, headers=self.headers, proxies=self.proxies)
            if res.status_code != requests.codes.ok:
                LOGGER.error("访问地址[%s], 返回的响应状态码为: %d" % (url, int(res.status_code)))
            return
        except Exception:
            LOGGER.exception("保存临时邮箱[%s]时遇到异常: " % self.email)
            return


if __name__ == '__main__':
    # with open('test.html', 'r', encoding='utf-16') as f:
    #     html_text = BeautifulSoup(f, 'html.parser')
    # mail_list = html_text.find('div', attrs={'class': 'inbox-dataList'}).find('ul').find_all('li')
    # for mail in reversed(mail_list):
    #     sender = mail.find(attrs={'class': re.compile('inboxSenderName')}).get_text()
    #     subject = mail.find(attrs={'class': re.compile('inboxSubject')}).get_text()
    #     print(sender + " : " + subject)
    #     href = mail.find('a', href=re.compile('https://temp-mail.org/en/view/')).get('href')
    #     print(href)
    # with open('test1.html', 'r', encoding='utf-8') as f:
    #     html_text = BeautifulSoup(f, 'html.parser')
    # code = html_text.find('div', attrs={'data-x-div-type': 'body'}).find('strong', text=re.compile('\\d+')).get_text()
    # print(code)
    exit(0)
