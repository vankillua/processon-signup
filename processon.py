#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import os
import random
import re
import string
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from captcha import Captcha
from captcha import CrackCaptchaException
from mails import TempMail
from tools import get_resource_file

# 根据当前文件获取当前路径
# CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))

# 日志句柄
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(module)s - %(threadName)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)


class ProcessOn(object):
    # ProcessOn网站地址
    PROCESSON_URL = r'https://www.processon.com'
    # chrome浏览器驱动路径
    CHROME_DRIVER = get_resource_file(relative_path=os.path.join('drivers', 'chromedriver.exe'), reference=__file__)
    # 破解滑动验证码最大尝试次数
    MAX_TRY_TIMES = 5

    def __init__(self, url, proxy, crack_times=MAX_TRY_TIMES, visual=False, logger=None):
        if logger:
            global LOGGER
            LOGGER = logger
        self.url = url
        self.proxy = proxy
        # 生成临时邮箱
        self.tm = TempMail(proxy=proxy, auto=True, logger=logger)
        self.email = self.tm.email
        self.password = ''.join(random.sample(string.ascii_letters + string.digits, 8))
        self.name = self.tm.username
        self.crack_times = crack_times
        LOGGER.info("临时邮箱: %s, 密码: %s" % (self.email, self.password))
        chrome_option = webdriver.ChromeOptions()
        # 非可视化, 即Chrome以无界面方式启动
        if not visual:
            chrome_option.add_argument('--headless')
        LOGGER.debug("ChromeDriver: %s" % self.CHROME_DRIVER)
        self.driver = webdriver.Chrome(executable_path=self.CHROME_DRIVER, options=chrome_option)
        self.driver.maximize_window()

    def run(self):
        # noinspection PyBroadException
        try:
            self.open()
            if not self.signup():
                LOGGER.error("邮箱[%s]注册失败!" % self.email)
                return False
            LOGGER.info("邮箱[%s]注册成功!" % self.email)
            # 关闭ProcessOn账号
            self.close_account()
            # 删除临时邮箱
            self.tm.delete_email()
            return True
        except Exception:
            LOGGER.exception("邮箱[%s]注册ProcessOn时遇到异常: " % self.email)
            return False
        finally:
            self.quit()

    def quit(self):
        if self.driver is not None:
            self.driver.quit()

    # 等待元素可点击
    def wait_click(self, element: WebElement, timeout: int = 10, frequency: int = 0.5):
        WebDriverWait(self.driver, timeout, frequency).until(lambda x: element).click()

    # 等待元素可点击
    def wait_clickable(self, locator, timeout: int = 10, frequency: int = 0.5):
        WebDriverWait(self.driver, timeout, frequency).until(EC.element_to_be_clickable(locator)).click()

    # 等待元素可输入
    def wait_send_keys(self, locator, value: str, timeout: int = 10, frequency: int = 0.5):
        WebDriverWait(self.driver, timeout, frequency).until(EC.presence_of_element_located(locator)).send_keys(value)

    # 等待图片加载完成
    def wait_image_loaded(self, element: WebElement, timeout: int = 10, frequency: int = 0.5):
        flag = False
        # noinspection PyBroadException
        try:
            # 当前时间戳
            start = time.time()
            js = 'return arguments[0].complete && ' \
                 'typeof arguments[0].naturalWidth != \"undefined\" ' \
                 '&& arguments[0].naturalWidth > 0'
            while time.time() - start < timeout:
                flag = self.driver.execute_script(js, element)
                if flag:
                    LOGGER.debug("图片加载完成: %f, %f" % (start, time.time()))
                    break
                else:
                    LOGGER.warning("图片加载未完成: %f, %f" % (start, time.time()))
                    time.sleep(frequency)
        except Exception:
            LOGGER.exception("等待图片加载时遇到异常: ")
        finally:
            return flag

    # 根据轨迹列表拖拽鼠标
    def drag_and_drop(self, element: WebElement, tracks: list):
        # 鼠标左键点击目标元素且不放开
        ActionChains(self.driver).click_and_hold(on_element=element).perform()
        time.sleep(0.2)
        for track in tracks:
            # 鼠标按轨迹移动
            ActionChains(self.driver).move_by_offset(xoffset=track, yoffset=0).perform()
            time.sleep(0.002)
        # 释放鼠标左键
        ActionChains(self.driver).release(on_element=element).perform()
        time.sleep(0.2)

    # 判断元素是否消失
    def is_element_dismiss(self, locator, timeout: int = 10, frequency: int = 0.5):
        try:
            WebDriverWait(self.driver, timeout, frequency).until_not(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    # 判断元素是否存在
    def is_element_exist(self, locator, timeout: int = 10, frequency: int = 0.5):
        try:
            WebDriverWait(self.driver, timeout, frequency).until(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    # 使用专属链接打开ProcessOn网站
    def open(self):
        # 浏览器打开ProcessOn用户专属邀请链接
        self.driver.get(self.url)
        # 点击"注册"按钮, 跳转到注册页面
        self.wait_clickable((By.XPATH, '//a[@href="/signup"]'))
        # self.wait_click(self.driver.find_element_by_xpath('//a[@href="/signup"]'))

    # 在ProcessOn网站注册用户
    def signup(self):
        self.wait_send_keys((By.ID, 'login_phone'), self.email)
        self.wait_send_keys((By.ID, 'login_password'), self.password)
        self.wait_send_keys((By.ID, 'login_fullname'), self.name)
        captcha = self.get_captcha()
        if not captcha:
            LOGGER.error("获取验证码失败!")
            return False
        self.wait_send_keys((By.ID, 'login_verify'), captcha)
        time.sleep(2)
        self.wait_clickable((By.ID, 'signin_btn'))
        # self.wait_click(self.driver.find_element_by_id('signin_btn'))
        # 如果注册成功, 页面会自动跳转, 根据页面元素是否存在来判断注册是否成功
        return self.is_element_exist((By.ID, 'user-logo'), 5)

    # 关闭ProcessOn网站账号
    def close_account(self):
        # noinspection PyBroadException
        try:
            session = requests.Session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/76.0.3809.100 Safari/537.36'
            }
            # 模拟登陆
            params = {'login_email': self.email, 'login_password': self.password}
            res = session.post(urljoin(self.PROCESSON_URL, r'/login'), headers=headers, params=params, verify=False)
            if res.status_code != requests.codes.ok:
                LOGGER.error("用户[%s]模拟登陆失败, 返回的响应状态码为: %d" % (self.email, int(res.status_code)))
                return False
            # 关闭账号
            params = {'reason': u'请求关闭账号！'}
            res = session.post(urljoin(self.PROCESSON_URL, r'/setting/account_close'), headers=headers,
                               params=params, verify=False)
            if res.status_code != requests.codes.ok:
                LOGGER.error("用户[%s]关闭账号失败, 返回的响应状态码为: %d, 返回的响应内容为: %s" % (self.email, int(res.status_code), res.text))
                return False
            LOGGER.info("用户[%s]关闭账号成功, 返回的响应状态码为: %d, 返回的响应内容为: %s" % (self.email, int(res.status_code), res.text))
            return True
        except Exception:
            LOGGER.exception("关闭账号时遇到异常: ")
            return False

    # 获取验证码
    def get_captcha(self):
        # noinspection PyBroadException
        try:
            LOGGER.info("开始破解滑动验证码!")
            # 点击"获取验证码"按钮
            self.wait_clickable((By.ID, 'tencent_btn'))
            # self.wait_click(self.driver.find_element_by_id('tencent_btn'))
            # 尝试破解滑动验证码
            if not self.crack_captcha():
                LOGGER.error("破解滑动验证码失败!")
                return ''
            LOGGER.info("破解滑动验证码成功!")
            # 从临时邮箱中获取验证码
            code = self.get_captcha_from_mail()
            if not code:
                LOGGER.error("从临时邮箱中获取验证码失败!")
                return ''
            LOGGER.info("从临时邮箱中获取的验证码: %s" % code)
            return code
        except Exception:
            LOGGER.exception("破解滑动验证码时遇到异常: ")
            return ''

    # 破解滑动验证码
    def crack_captcha(self):
        flag = True
        count = 1
        while count <= self.crack_times:
            # noinspection PyBroadException
            try:
                # 等待验证码提示框出现
                WebDriverWait(self.driver, 10, 0.5).until(EC.presence_of_element_located((By.ID, 'tcaptcha_transform')))
                # 切换iframe
                self.driver.switch_to.frame(self.driver.find_element_by_css_selector('iframe#tcaptcha_iframe'))

                # 生成验证码操作类实例
                captcha = Captcha()

                # 定位验证码图片并下载到本地(背景大图, 滑块小图)
                background = self.driver.find_element_by_id('slideBg')
                if not self.wait_image_loaded(background):
                    raise CrackCaptchaException("加载背景大图失败!")
                # 获取src属性值
                bg_url = background.get_attribute('src')
                if not captcha.download_image(bg_url, 'bg_block.png'):
                    raise CrackCaptchaException("下载背景大图[%s]失败!" % bg_url)

                slide_block = self.driver.find_element_by_id('slideBlock')
                sb_url = slide_block.get_attribute('src')
                if not captcha.download_image(sb_url, 'sb_block.png'):
                    raise CrackCaptchaException("下载滑块小图[%s]失败!" % sb_url)

                # 获取页面图片大小及位置
                bg_width = background.size['width']
                bg_loc_x = background.location['x']
                sb_loc_x = slide_block.location['x']

                # 获取原图大小
                actual_width, actual_height = captcha.get_size('bg_block.png')

                # 获取滑块原图在背景原图中的位置, 即(行, 列)坐标
                # 行坐标即距离top的长度, 列坐标即距离left的长度
                position = captcha.get_position('bg_block.png', 'sb_block.png', False)

                # 按比例换算页面滑块图片在页面背景图片中的位置
                slide_position_x = int(bg_width / actual_width * position[1])
                # 页面滑块图片活动距离
                slide_distance = slide_position_x - (sb_loc_x - bg_loc_x)

                track_list = captcha.get_track(slide_distance)
                # 定位滑块
                drag_button = self.driver.find_element_by_id('tcaptcha_drag_button')
                # 滑动滑块
                self.drag_and_drop(drag_button, track_list)

                # 判断是否成功
                if self.is_element_dismiss((By.ID, 'tcWrap'), 2):
                    flag = True
                    LOGGER.info("第%d次尝试破解滑动验证码: 成功!" % count)
                    break
                else:
                    flag = False
                    raise CrackCaptchaException("第%d次尝试破解滑动验证码: 失败!" % count)
            except CrackCaptchaException as cce:
                LOGGER.error(str(cce))
                count += 1
                # 点击刷新按钮, 重新加载验证码
                self.wait_clickable((By.ID, 'reload'))
                # self.wait_click(self.driver.find_element_by_id('reload'))
                time.sleep(1)
                # 切换回默认dom树
                self.driver.switch_to.default_content()
                continue
            except Exception as e:
                raise e
        return flag

    # 从邮件中获取验证码
    def get_captcha_from_mail(self):
        # noinspection PyBroadException
        try:
            content = self.tm.get_mail_content(sender='ProcessOn', subject='ProcessOn验证码')
            html = BeautifulSoup(content, 'html.parser')
            return html.find('div', attrs={'data-x-div-type': 'body'}).find('strong', text=re.compile('\\d+')).get_text()
        except Exception:
            LOGGER.exception("")
            return ''


if __name__ == '__main__':
    # main_process(r'https://www.processon.com/i/5cc564f5e4b09eb4ac2b498e', 1)
    # sim_login('ojvy9ulw@it-simple.net', 'mxBQEG1H')
    exit(0)
