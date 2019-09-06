#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

from proxies import ProxyPool
from processon import ProcessOn

# 日志句柄
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(module)s - %(threadName)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)


# 主进程
def main_process(url, numbers=10, visual=False, logger=None):
    """
    :param url: ProcessOn专属邀请链接, 如: https://www.processon.com/i/5cc564f5e4b09eb4ac2b498e
    :param numbers: 邀请注册人数, 注: 邀请1人注册成功, 增加3个文件数
    :param visual: 可视化标识, 非可视化即浏览器以无界面启动
    :param logger: GUI的日志句柄
    :return:
    """
    if logger:
        global LOGGER
        LOGGER = logger
    stats = {'success': 0, 'failure': 0}
    # noinspection PyBroadException
    try:
        # 获取代理
        proxy_pool = ProxyPool(logger=logger)
        ps = proxy_pool.get_proxy(num=numbers, to_csv=False)
        for p in ps:
            po = ProcessOn(url=url, proxy=p, visual=visual, logger=logger)
            if not po:
                LOGGER.error("实例化ProcessOn失败!")
                break
            if po.run():
                stats['success'] += 1
            else:
                stats['failure'] += 1
        LOGGER.info("注册成功人数: %d, 注册失败人数: %d" % (stats['success'], stats['failure']))
        return stats['success'] != 0
    except Exception:
        LOGGER.exception("主进程运行时遇到异常: ")
        return False


if __name__ == '__main__':
    exit(0)
