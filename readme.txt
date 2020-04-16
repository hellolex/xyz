# XYZ博客后端系统
开发语言Python3，使用框架django 2.2

# 系统介绍
前后端分离部署
使用waitree服务器，已配置在django系统里，直接启动即可
多用户，每个注册用户有属于自己的主页，游客可访问
采用JWT结合数据库进行访问验证，验证方式为令牌验证，访问令牌默认7天过期
支持服务器图片上传或七牛图片上传
文章管理
评论管理

# 示例
前端效果仅参考
http://blog.chenyuhuan.site/testuser001/home

# 安装数据库mysql
创建数据库xyz，运行xyz.sql创建表

# 安装项目
1、准备好python环境，电脑要先安装python，virtualenv
2、下载项目
3、在server文件夹目录下运行如下命令创建一个虚拟环境
```
virtualenv env
```
4、进入 env\Scripts 目录，运行如下命令激活虚拟环境
```
activate
```
5、返回到server文件夹根目录，运行如下命令安装项目依赖
```
pip install -r requirements.txt
```
这样项目就安装好了

# 配置项目
1、在xyz文件夹中打开 settings.py 文件配置 mysql 服务器
2、在xyz -> apps -> blog文件夹中打开文件 views.py 配置上传的本地文件夹
3、最后打开 server.py 文件，填写激活虚拟文件绝对路径，该文件在env/Scripts文件夹下
```
activate_this= os.path.join("E:/XYZ/server/env/Scripts/activate_this.py")
```
服务器端口默认8000，可自行修改

# 运行
在server文件夹下运行如下命令启动服务器
```
python server.py
```
# 接口
详情见接口文档

