#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import os
import random
import time

import cv2
import numpy as np
import requests
from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from tools import get_resource_path

# 根据当前文件获取当前路径
# CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))

# 日志句柄
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(module)s - %(threadName)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)


# 自定义异常类
class CrackCaptchaException(Exception):
    def __init__(self, err='破解验证码错误'):
        Exception.__init__(self, err)


# 浏览器驱动类
# class Chrome(object):
#     # chrome浏览器驱动路径
#     CHROME_DRIVER = os.path.join(CURRENT_PATH, 'drivers', 'chromedriver.exe')
#     # web地址
#     # WEB_URL = r'https://open.captcha.qq.com/online.html'
#     WEB_URL = r'https://www.processon.com/signup'
#     # 最大尝试次数
#     MAX_TRY_TIMES = 5
#
#     def __init__(self, url=WEB_URL, max_times=MAX_TRY_TIMES):
#         self.url = url
#         self.max_times = max_times
#         chrome_option = webdriver.ChromeOptions()
#         self.driver = webdriver.Chrome(executable_path=self.CHROME_DRIVER, chrome_options=chrome_option)
#         self.driver.maximize_window()
#
#     def quit(self):
#         if self.driver is not None:
#             self.driver.quit()
#
#     # 测试腾讯防水墙官网的滑动验证码
#     def goto_open_captcha(self):
#         self.driver.get(self.WEB_URL)
#         # 点击"可疑用户"tab页
#         self.wait_click(self.driver.find_element_by_css_selector('.wp-onb-tit>a[data-type="1"]'))
#         # 点击"体验验证码"按钮
#         self.wait_click(self.driver.find_element_by_id('code'))
#
#     # 测试ProcessOn官网的滑动验证码
#     def goto_processon_signup(self):
#         self.driver.get(self.WEB_URL)
#         # 点击"获取验证码"按钮
#         self.wait_click(self.driver.find_element_by_id('tencent_btn'))
#
#     def wait_click(self, element, timeout=10, frequency=0.5):
#         WebDriverWait(self.driver, timeout, frequency).until(lambda x: element).click()
#
#     def wait_image_load(self, element, timeout=10, frequency=0.5):
#         flag = False
#         # noinspection PyBroadException
#         try:
#             # 当前时间戳
#             start = time.time()
#             js = 'return arguments[0].complete && ' \
#                  'typeof arguments[0].naturalWidth != \"undefined\" ' \
#                  '&& arguments[0].naturalWidth > 0'
#             while time.time() - start < timeout:
#                 flag = self.driver.execute_script(js, element)
#                 if flag:
#                     LOGGER.info("图片加载完成: %f, %f" % (start, time.time()))
#                     break
#                 else:
#                     LOGGER.warning("图片加载未完成: %f, %f" % (start, time.time()))
#                     time.sleep(frequency)
#         except Exception:
#             LOGGER.exception("等待图片加载时遇到异常: ")
#         finally:
#             return flag
#
#     def drag_and_drop(self, element, tracks):
#         # 鼠标左键点击目标元素且按住不放
#         ActionChains(self.driver).click_and_hold(on_element=element).perform()
#         time.sleep(0.2)
#         for track in tracks:
#             # 鼠标按轨迹移动
#             ActionChains(self.driver).move_by_offset(xoffset=track, yoffset=0).perform()
#             time.sleep(0.002)
#         # 释放鼠标
#         ActionChains(self.driver).release(on_element=element).perform()
#         time.sleep(0.2)
#
#     def is_element_dismiss(self, locator, timeout=10, frequency=0.5):
#         try:
#             WebDriverWait(self.driver, timeout, frequency).until_not(EC.presence_of_element_located(locator))
#             return True
#         except TimeoutException:
#             return False
#
#     def captcha_crack(self):
#         # self.goto_open_captcha()
#         self.goto_processon_signup()
#
#         flag = True
#         count = 1
#         while count <= self.MAX_TRY_TIMES:
#             # noinspection PyBroadException
#             try:
#                 # 等待验证码提示框出现
#                 WebDriverWait(self.driver, 10, 0.5).until(EC.presence_of_element_located((By.ID, 'tcaptcha_transform')))
#                 # 切换iframe
#                 self.driver.switch_to.frame(self.driver.find_element_by_css_selector('iframe#tcaptcha_iframe'))
#
#                 # 生成验证码操作类实例
#                 captcha = Captcha()
#
#                 # 定位验证码图片并下载到本地(背景大图, 滑块小图)
#                 background = self.driver.find_element_by_id('slideBg')
#                 if not self.wait_image_load(background):
#                     raise CrackCaptchaException("加载背景大图失败!")
#                 bg_url = background.get_attribute('src')
#                 if not captcha.download_image(bg_url, 'bg_block.png'):
#                     raise CrackCaptchaException("下载背景大图[%s]失败!" % bg_url)
#
#                 slide_block = self.driver.find_element_by_id('slideBlock')
#                 sb_url = slide_block.get_attribute('src')
#                 if not captcha.download_image(sb_url, 'sb_block.png'):
#                     raise CrackCaptchaException("下载滑块小图[%s]失败!" % sb_url)
#
#                 # 获取页面图片大小及位置
#                 bg_width = background.size['width']
#                 bg_loc_x = background.location['x']
#                 sb_loc_x = slide_block.location['x']
#
#                 # 获取原图大小
#                 actual_width, actual_height = captcha.get_size('bg_block.png')
#
#                 # 获取滑块原图在背景原图中的位置, 即(行, 列)坐标
#                 # 行坐标即距离top的长度, 列坐标即距离left的长度
#                 position = captcha.get_position('bg_block.png', 'sb_block.png', True)
#
#                 # 按比例换算页面滑块图片在页面背景图片中的位置
#                 slide_position_x = int(bg_width / actual_width * position[1])
#                 # 页面滑块图片活动距离
#                 slide_distance = slide_position_x - (sb_loc_x - bg_loc_x)
#
#                 track_list = captcha.get_track(slide_distance)
#                 # 定位滑块
#                 drag_button = self.driver.find_element_by_id('tcaptcha_drag_button')
#                 # 滑动滑块
#                 self.drag_and_drop(drag_button, track_list)
#
#                 # 判断是否成功
#                 if self.is_element_dismiss((By.ID, 'tcWrap'), 2):
#                     flag = True
#                     LOGGER.info("第%d次尝试破解滑动验证码: 成功!" % count)
#                     break
#                 else:
#                     flag = False
#                     raise CrackCaptchaException("第%d次尝试破解滑动验证码: 失败!" % count)
#             except CrackCaptchaException as cce:
#                 LOGGER.error(str(cce))
#                 count += 1
#                 # 点击刷新按钮, 重新加载验证码
#                 self.wait_click(self.driver.find_element_by_id('reload'))
#                 time.sleep(1)
#                 # 切换回默认dom树
#                 self.driver.switch_to.default_content()
#                 continue
#             except Exception as e:
#                 raise e
#         return flag


# 验证码操作类
class Captcha(object):
    IMAGE_PATH = get_resource_path('images')

    def __init__(self, logger=None):
        if logger:
            global LOGGER
            LOGGER = logger
        os.makedirs(self.IMAGE_PATH, 0o755, True)

    # 下载原图
    def download_image(self, url, name):
        # noinspection PyBroadException
        try:
            if os.path.isdir(self.IMAGE_PATH):
                response = requests.get(url)
                content = response.content
                with open(os.path.join(self.IMAGE_PATH, name), 'wb') as f:
                    f.write(content)
                return True
            else:
                return False
        except Exception:
            LOGGER.exception("下载图片时遇到异常: ")
            return False

    # 读取原图
    def read_image(self, filename, flags=None):
        file_path = filename if os.path.isfile(filename) else os.path.join(self.IMAGE_PATH, filename)
        if os.path.isfile(file_path):
            if flags:
                return cv2.imread(file_path, flags)
            else:
                return cv2.imread(file_path)
        else:
            LOGGER.error("输入的原图[%s]不存在, 请检查!" % file_path)
            return None

    # 获取原图大小, image: 原图名称
    def get_size(self, image):
        img = self.read_image(image)
        h, w = img.shape[:2]
        return w, h

    # 获取滑块小图匹配背景大图缺口位置
    def get_position(self, background_image, slide_image, show=False):
        """
            background_image: 背景图片名称
            slide_image: 滑块图片名称
        """
        # 读取为灰度图
        background = self.read_image(background_image, cv2.IMREAD_GRAYSCALE)
        slide = self.read_image(slide_image, cv2.IMREAD_GRAYSCALE)
        # 图像反色
        bg_gray_anti = abs(255 - background)
        # 获取背景灰度反色图与滑块灰度图匹配结果
        result = cv2.matchTemplate(bg_gray_anti, slide, cv2.TM_CCOEFF_NORMED)
        # 获取匹配结果中最大匹配的位置
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        if show:
            # 在背景灰度反色图中框出匹配滑块下图的位置
            h, w = slide.shape[:2]
            cv2.rectangle(bg_gray_anti, max_loc, (max_loc[0] + w, max_loc[1] + h), 255, 2)
            cv2.imshow('bg', bg_gray_anti)
            # 等待任意按键退出, 最长等待2000ms
            cv2.waitKey(2000)
            # 关闭所有窗口
            cv2.destroyAllWindows()
        # 获取匹配结果最大值在匹配结果二维数组中的索引, 即(行, 列)坐标
        # 行坐标: 距离top的长度, 列坐标: 距离left的长度
        row, col = np.unravel_index(result.argmax(), result.shape)
        LOGGER.debug("匹配位置: (%d, %d)" % (row, col))
        return row, col

    # 计算滑动轨迹
    @staticmethod
    def get_track(distance):
        """
        拿到移动轨迹, 模仿人的滑动行为, 先匀加速后匀减速
        匀变速运动基本公式:
        ① v = v0 + at
        ② s = v0t + (1/2)at²
        ③ v² - v0² = 2as

        :param distance: 需要移动的距离
        :return: 存放每0.2秒移动的距离
        """
        # 初速度
        v = 0
        # 单位时间为0.2s来统计轨迹, 轨迹即0.2内的位移
        t = 0.2
        # 位移/轨迹列表, 列表内的一个元素代表0.2s的位移
        tracks = []
        # 当前的位移
        current = 0
        # 到达mid值开始减速
        mid = int(distance * 7 / 8)

        # 先滑过一点, 最后再反着滑动回来
        over = 10
        distance += over
        while current < distance:
            # 加速度越小, 单位时间的位移越小, 模拟的轨迹就越多越详细
            if current < mid:
                # 加速运动
                a = random.randint(2, 10)
            else:
                # 减速运动
                a = -random.randint(3, 15)

            # 初速度
            v0 = v
            # 0.2秒时间内的位移
            s = int(v0 * t + 0.5 * a * (t ** 2))
            s = s if s > 1 else 1
            # 当前的位置
            current += s
            # 添加到轨迹列表
            tracks.append(s)

            # 速度已经达到v, 该速度作为下次的初速度
            v = v0 + a * t

        # 滑动超过的实际值
        over += current - distance
        o = over
        # 反向滑动到准确位置
        for i in range(int(over)):
            if o <= 3:
                tracks.append(-o)
                break
            else:
                r = -random.randint(1, 3)
                tracks.append(r)
                o += r

        return tracks


# def main_process():
#     chrome = None
#     # noinspection PyBroadException
#     try:
#         chrome = Chrome()
#         chrome.captcha_crack()
#         return True
#     except Exception:
#         LOGGER.exception("执行时遇到异常: ")
#         return False
#     finally:
#         if chrome is not None:
#             chrome.quit()


if __name__ == "__main__":
    exit(0)
