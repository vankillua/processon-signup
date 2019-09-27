#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import logging
from pandas import DataFrame
import queue
import re
import threading
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# 代理网站
WEB_URL = r'https://www.xicidaili.com/nn/'

# 代理网站每页数量
PAGE_NUM = 100

# 最大代理数
MAX_PROXY_NUM = 200

# 最大线程数
MAX_THREADS = 8

# 输出代理的csv文件
CSV_FILE = r'proxies.csv'

# 时间信息
TIME_INFO = {
    # 主线程休眠时间
    'MAIN_THREAD_SLEEP_TIME': 5,

    # 主线程总等待时间
    'MAIN_THREAD_WAIT_TIME': 360,

    # 子线程JOIN时间
    'SUB_THREAD_JOIN_TIME': 2,

    # 请求超时时间
    'REQUEST_TIMEOUT': 60,

    # 请求短超时时间
    'REQUEST_SHORT_TIMEOUT': 2,
}

# 日志句柄
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(module)s - %(threadName)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings()


# 代理池
class ProxyPool(object):
    def __init__(self, logger=None):
        if logger:
            global LOGGER
            LOGGER = logger

    # 获取代理
    def get_proxy(self, num: int = MAX_PROXY_NUM, to_csv: bool = False):
        proxies = []
        # noinspection PyBroadException
        try:
            page = 1
            while len(proxies) < num:
                url = urljoin(WEB_URL, str(page))
                html = self.get_html(url)
                if not html:
                    LOGGER.error("访问代理网站[%s]失败!" % url)
                    break
                # 从html中提取代理详细信息
                details = self.get_details(html)
                if details:
                    length = len(details)
                    times = int(length / num) + 1 if length % num > 0 else int(length / num)
                    for i in range(times):
                        arr = details[i * num:(i + 1) * num] if i < times - 1 else details[i * num]
                        # 验证代理有效性
                        for a in self.check_proxy(arr):
                            proxies.append(a[0])
                        if len(proxies) >= num:
                            break
                # 设置退出条件, 防止死循环
                if page > int(num / PAGE_NUM + 10):
                    break
                page += 1
            if to_csv:
                if not self.output_proxy(proxies):
                    LOGGER.error("输出可用代理到csv文件失败!")
            return proxies
        except Exception:
            LOGGER.exception("获取代理时遇到异常: ")
            return proxies

    # 访问代理网站获取html
    @staticmethod
    def get_html(url):
        html = None
        # noinspection PyBroadException
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/76.0.3809.100 Safari/537.36'
            }
            res = requests.get(url, headers=headers, verify=False)
            content = res.text
            if res.status_code != requests.codes.ok:
                LOGGER.error("访问地址[%s], 返回的响应状态码为: %d" % (url, int(res.status_code)))
            else:
                # 通过BeautifulSoup解析响应的html正文
                html = BeautifulSoup(content, 'html.parser')
            return html
        except Exception:
            LOGGER.exception("获取[%s]地址的html内容时遇到异常: " % url)
            return html

    # 获取详细信息
    @staticmethod
    def get_details(html):
        details = []
        # noinspection PyBroadException
        try:
            # 获取#ip_list下的全部tr
            trs = html.find('table', id='ip_list').find_all('tr')
            # 忽略表格头部, 即第一行
            for tr in trs[1:]:
                # 国家, IP地址, 端口, 服务器地址, 是否匿名, 类型, 速度, 连接时间, 存活时间, 验证时间
                tds = tr.find_all('td')
                # 忽略字段数小于7的行
                if len(tds) < 7:
                    continue
                if tds[0].find('img') is None:
                    nation = '未知'
                    locate = '未知'
                else:
                    nation = tds[0].find('img')['alt'].strip()
                    locate = tds[3].text.strip()
                ip = tds[1].text.strip()
                port = tds[2].text.strip()
                anonymous = tds[4].text.strip()
                protocol = tds[5].text.strip()
                # 忽略类型不是HTTP或HTTPS的代理
                if not str(protocol).upper().startswith('HTTP'):
                    continue
                speed = tds[6].find('div')['title'].strip()
                obj = re.search(r'([\d.]+)', speed)
                speed = obj.group() if obj else speed
                # 忽略速度大于2秒的代理
                if float(speed) > 2:
                    continue
                details.append([nation, ip, port, locate, anonymous, protocol, speed])
            return details
        except Exception:
            LOGGER.exception("从html中获取详细信息时遇到异常: ")
            return details

    # 验证代理
    def check_proxy(self, data: list):
        proxies = []
        # noinspection PyBroadException
        try:
            thread_name = '验证代理有效性'
            worker_threads = MAX_THREADS if len(data) >= MAX_THREADS else len(data)
            worker_queue = queue.Queue(len(data))
            result_queue = queue.Queue(len(data))

            # 验证代理有效性任务添加到工作队列
            for d in data:
                # IP, 端口, 类型
                worker_queue.put((d[1], d[2], d[5]))

            # 多线程重建数据库
            self.thread_operations(self.verify_proxy, worker_threads, thread_name, worker_queue, result_queue)

            # 处理线程返回的结果
            flag, proxies = self.handle_result_queue(thread_name, 2, len(data), result_queue)
            return proxies
        except Exception:
            LOGGER.exception("验证代理时遇到异常: ")
            return proxies

    # 验证代理有效性
    @staticmethod
    def verify_proxy(worker_queue: queue.Queue, result_queue: queue.Queue):
        # IP, 端口, 类型
        input_param_num = 3
        while not worker_queue.empty():
            items = worker_queue.get()
            if not isinstance(items, tuple) or len(items) < input_param_num:
                LOGGER.error("验证代理有效性线程从工作队列获取的元素[%s]格式错误, 将不会被处理!" % str(items))
                continue
            ip, port, protocol = items[:input_param_num]
            proxy = str(protocol).lower() + "://" + ip + ":" + port
            # noinspection PyBroadException
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/76.0.3809.100 Safari/537.36'
                }
                proxies = {str(protocol).lower(): proxy}
                res = requests.get(r'https://www.processon.com', headers=headers, proxies=proxies,
                                   timeout=TIME_INFO['REQUEST_SHORT_TIMEOUT'])
                if res.status_code != requests.codes.ok:
                    LOGGER.error("代理[%s]不可用" % proxy)
                    result_queue.put((False, proxy))
                else:
                    LOGGER.debug("代理[%s]可用" % proxy)
                    result_queue.put((True, proxy))
            except Exception:
                LOGGER.error("代理[%s]不可用" % proxy)
                # LOGGER.exception("验证代理有效性[%s]时遇到异常: " % proxy)
                result_queue.put((False, proxy))

    # 线程操作
    @staticmethod
    def thread_operations(thread_func, total_threads: int, thread_name: str, *args):
        # noinspection PyBroadException
        try:
            begin_time = datetime.datetime.now()
            threads = []
            joined_threads = 0

            # 创建线程
            for i in range(0, total_threads):
                threads.append(threading.Thread(target=thread_func, args=args))

            # 启动线程
            for t in threads:
                t.start()
                time.sleep(0.1)

            # 收割线程
            while (datetime.datetime.now() - begin_time).seconds <= TIME_INFO['MAIN_THREAD_WAIT_TIME']:
                if joined_threads >= total_threads:
                    LOGGER.info("%s的全部子线程都已执行完成!" % thread_name)
                    break
                i = 0
                while i < len(threads):
                    threads[i].join(TIME_INFO['SUB_THREAD_JOIN_TIME'])
                    if threads[i].is_alive():
                        LOGGER.info("%s的子线程[%s]未执行完成, 继续等待..." % (thread_name, threads[i].getName()))
                        i += 1
                    else:
                        LOGGER.info("%s的子线程[%s]执行完成!" % (thread_name, threads[i].getName()))
                        joined_threads += 1
                        del threads[i]
                if threads:
                    time.sleep(TIME_INFO['MAIN_THREAD_SLEEP_TIME'])

            if len(threads) > 0:
                LOGGER.error("等待[%d]秒后, 仍然有%s的子线程未执行完成!" % (TIME_INFO['MAIN_THREAD_WAIT_TIME'], thread_name))
                return False
            return True
        except Exception:
            LOGGER.exception("线程操作时遇到异常: ")
            return False

    # 处理结果队列
    @staticmethod
    def handle_result_queue(thread_name: str, result_size: int, expect_success: int, result_queue: queue.Queue):
        success = []
        flag = True
        # noinspection PyBroadException
        try:
            # 从结果队列中获取结果, 全部任务执行成功才算成功
            while not result_queue.empty():
                result = result_queue.get()
                if not isinstance(result, tuple) or len(result) < result_size:
                    LOGGER.error("%s线程返回结果的格式错误, 将会被忽略!" % thread_name)
                    continue
                if result[0]:
                    LOGGER.info("%s[%s]成功!" % (thread_name, str(result[1])))
                    success.append(result[1:result_size])
                else:
                    LOGGER.error("%s[%s]失败!" % (thread_name, result[1]))
                    flag = False
            # 执行成功数比预期少则认为失败
            if len(success) < expect_success:
                flag = False
        except Exception:
            LOGGER.exception("处理%s线程的结果队列时遇到异常: " % thread_name)
            flag = False
        return flag, success

    # 输出可用代理到csv文件
    @staticmethod
    def output_proxy(data: list):
        # noinspection PyBroadException
        try:
            o = {'proxy': data}
            df = DataFrame(o)
            df.to_csv(CSV_FILE, index=False, encoding='cp936')
            return True
        except Exception:
            LOGGER.exception("输出可用代理到csv文件时遇到异常: ")
            return False


if __name__ == '__main__':
    # pp = ProxyPool()
    # pp.get_proxy(3, True)
    exit(0)
