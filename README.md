# openai注册机

## 介绍
基于浏览器方案的openai注册机

## 免责声明
本项目仅供学习交流使用，严禁用于商业用途，否则后果自负。

## 使用方法
### 前置准备
- 一个支持openai注册的域名，比如`example.com`
- 一个支持`catch all`的收件服务，比如cloudflare或者自建的邮箱服务器
- 一个用于接受`catch all`邮件的且支持imap协议的邮箱，比如`outlook`、`gmail`

### 开始使用

1. 配置邮箱  
配置好你前序准备的域名和邮箱，保证所有openai的邮件都会转发到你的支持imap协议的邮箱中。
2. 克隆本项目
```bash
git clone https://github.com/MagicalMadoka/openai-signup-tool.git

cd openai-signup-tool
```

3. 重命名`config/config.json.example`为`config/config.json`

- `domain`: 必填，你注册用的域名。
- `proxy`: 选填，代理地址。正常的URL格式例如：`http://user:password@123.45.67.89:8080`。如果是多个用`;`进行分割，会自动随机选择一个进行使用。
  - 背后最好使用高质量的代理池，可以减少过cf和arkose的麻烦。如果代理服务器运行在你的本地，请使用`host.docker.internal`替换掉`127.0.0.1`
  - 请注意在一次注册上下文中会使用一个固定的代理地址，因此如果你的代理是动态的，那么他的生效时间应该需要大于一次注册的时间。
- `clientKey`: 选填，[yescaptcha](https://yescaptcha.com/i/oFmkQz)的clientKey，如果出现验证码，会尝试进行打码。
- `emailWorkerNum`: 必填，处理邮件的线程个数，根据机器的配置自行决定。
- `signupWorkerNum`: 必填，注册线程的个数，根据机器的配置自行决定。
- `emailAddr`: 必填，你的邮箱地址。
- `emailPassword`: 必填，你的邮箱密码，或应用密码。这取决于你的邮箱服务的提供方。
- `emailImapServer`: 必填，你的邮箱的imap服务器地址，一般可以在你邮箱服务的提供方的文档中找到。
- `emailImapPort`: 选填，你的邮箱的imap服务器端口，一般可以在你邮箱服务的提供方的文档中找到。

4. 运行
```bash
docker compose up -d
```
注册成功的账号会出现在`data/accounts.txt`中。如果账号被授权了额度，会额外提取sess到`data/sess.txt`中。

## 其他说明
- 本项目使用的过cf方案是免费的，耗时可能较长。最差的情况下况下，一分钟左右也是可以过的，如果过不了检查一下你的ip。
- 本项目在一个正常延时的网络和一个配置正常的机器下测试运行正常，所以如果出现问题，可以先排查网络和机器的问题。当然也欢迎你补充一些异常处理的代码。
- 该方案是基于浏览器的方案，内存不要给的太少，否则会异常退出。

## 参考项目
- https://github.com/FlareSolverr/FlareSolverr

## 交流沟通
- 本项目相关的讨论请提[issues](https://github.com/MagicalMadoka/openai-signup-tool/issues)。先点star哦。
- 其他技术交流: [Telegram](https://t.me/+iNf8qQk0KUpkYmEx)

## 帮助我训练模型
我正在维护一些打码模型，并且放出来训练好的参数供大家免费使用,项目地址是[funcaptcha-challenger](https://github.com/MagicalMadoka/funcaptcha-challenger)
但是缺少更多的训练数据，如果你配置了打码服务，并且乐于帮助我，你可以把`data/solved`目录下的图片发给[我的机器人](https://t.me/madokax_bot)
