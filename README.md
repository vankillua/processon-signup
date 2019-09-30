# processon-signup
模拟使用ProcessOn邀请链接进行注册

## 实现流程
1. 通过代理网站`https://www.xicidaili.com`获取代理IP和端口
2. 通过临时邮箱API`https://api4.temp-mail.org/request/`获取邮箱域名，并随机生成临时邮箱地址
3. 通过OpenCV破解腾讯防水墙可疑用户级别验证码
4. 通过BeautifulSoup从html邮件中提取验证码

### 使用方法
1. 如果没有安装pipenv则需要先安装，`pip install pipenv`
2. 克隆项目后，使用pipenv把依赖安装到虚拟环境，`pipenv install`
3. 可以在PyCharm等Python IDE上直接运行或命令行运行，入口脚本：gui.py 或 handler.py
4. 也可以打包成exe来使用

### 温馨提示
1. 代理和临时邮箱都是依赖外部资源，容易由于网络问题而导致工具无法使用
2. 临时邮箱API有时候会特别慢，甚至超时；可以到RapidAPI网站订阅这个API`https://rapidapi.com/Privatix/api/temp-mail`，但需要绑定信用卡，访问量超出时会扣费
3. 破解滑动验证码并不是百分百成功，但测试过程中都能在设置的重试次数范围内破解成功
4. 有时候点击“立即注册”按钮后页面没有反应，实际上是因为调注册接口时返回“账号有误”，可能需要合理地创建账号才能解决
`https://www.processon.com/signup/submit
{"result":"error","errorcode":"error_account","msg":"账号有误"}`
