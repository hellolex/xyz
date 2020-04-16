import sys
import os
import jwt
import datetime
import time
import xlwt
import ast
from io import StringIO,BytesIO
from django.shortcuts import render,render_to_response
from django.http import HttpResponse,JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import User,UserLogin,Article,Category,Comment,ArticleTop,Blog
from django.db.models import Q,F
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.forms.models import model_to_dict
from django.db.models import Avg, Max, Min, Count, Sum

from xyz.custom import _setResult, _errlog, FieldValidator, sms, genID

#本地上传图片保存的文件夹，相对于根文件夹
file_url = '../web/upload/'

#保存到数据库的文件访问通用前缀
file_access_prefix = '/upload/'

#创建一个验证器实例
fv = FieldValidator()

#令牌验证装饰器
def auth(func):
    from functools import wraps
    @wraps(func)
    def authed(request, *args, **kwargs):
        res = isLogin(request)
        if res[0] == True:
            return func(request, res[1], *args, **kwargs)
        else:
            return _setResult(error=res[2],data=res[2],code=res[3])
    return authed

#令牌验证 是否登录
def isLogin(request):
    errorstr = None
    data = None
    code = None
    try:
        auth_header = request.META.get('HTTP_AUTHORIZATION').split()
    except AttributeError:
        _errlog('缺少认证参数', sys._getframe().f_code.co_name)
        errorstr = '无效授权'
        code = 810101
        return False,data,errorstr,code
    if auth_header[0].lower() == 'token':
        #先无验证解码令牌获取用户信息
        try:
            origin_payload = jwt.decode(auth_header[1], verify=False)
        except Exception as e:
            _errlog('无效令牌1 ' + str(e), sys._getframe().f_code.co_name)
            errorstr = '无效授权'
            code = 810101
            return False,data,errorstr,code
        #如果登录表里无此用户则说明用户未登录
        try:
            ul = UserLogin.objects.get(user_id=origin_payload.get('user',None))
        except UserLogin.DoesNotExist:
            _errlog('对应令牌未找到用户', sys._getframe().f_code.co_name)
            errorstr = '无效授权'
            code = 810101
            return False,data,errorstr,code
        #如果登录表里的用户令牌跟请求令牌不一致，说明请求令牌无效了
        if ul.token != auth_header[1]:
            _errlog('令牌不一致', sys._getframe().f_code.co_name)
            errorstr = '无效授权'
            code = 810101
            return False,data,errorstr,code
        #开始检验
        try:
            payload = jwt.decode(auth_header[1], settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            _errlog('令牌过期', sys._getframe().f_code.co_name)
            errorstr = '无效授权'
            code = 810101
            #检验不通过，删除数据库中的令牌，返回错误
            ul.delete()
            return False,data,errorstr,code
        except jwt.InvalidTokenError:
            _errlog('令牌无效', sys._getframe().f_code.co_name)
            errorstr = '无效授权'
            code = 810101
            #检验不通过，删除数据库中的令牌，返回错误
            ul.delete()
            return False,data,errorstr,code
        except Exception as e:
            _errlog('令牌解码失败 ' + str(e), sys._getframe().f_code.co_name)
            errorstr = '无效授权'
            code = 810101
            #检验不通过，删除数据库中的令牌，返回错误
            ul.delete()
            return False,data,errorstr,code
        else:
            #检验通过
            try:
                user = User.objects.get(id=payload['user']) #如果找到多条或找不到会抛出错误
            except User.DoesNotExist:
                errorstr = '找不到该用户'
                return False,data,errorstr,code
            #通过检验的接口函数会有第二个参数为当前用户模型
            return True,user
    else:
        _errlog('不支持的认证类型', sys._getframe().f_code.co_name)
        errorstr = '无效授权'
        code = 810101
        return False,data,errorstr,code

#用户注册 注册成功后自动设置博客信息表
def reg(request):
    if request.method == 'POST':
        login_name = request.POST.get('login_name', None)
        login_pw = request.POST.get('login_pw', None) #这个密码要求前端使用MD5加密
        email = request.POST.get('email', None)
        
        vd = {
            'loginname':[[login_name, 3, 20],fv.isUserID],
            'loginpw':[[login_pw, 6],fv.isPW],
            'email':[[email,0,0], fv.isEmail]
        }
        if fv.validator(validatdict = vd)[0] is False:
            #检测是否为空，格式是否正确
            errorstr = fv.validator(validatdict = vd)[1]
            _errlog(errorstr, sys._getframe().f_code.co_name)
            return _setResult(error=errorstr)
        #检测是否重复
        try:
            user = User.objects.get(login_name=login_name) #如果找到多条或找不到会抛出错误
        except User.DoesNotExist:
            #保存用户数据
            user = User()
            user.login_name = login_name
            user.login_pw = login_pw #前端已经MD5加密，此处无需再次加密，可在此设置安全规则
            user.email = email
            user.nickname = login_name
            user.datetime_reg = time.strftime("%Y-%m-%d %H:%M:%S")
            user.domain = login_name
            user.avatar = '/static/img/avatar.jpg'
            user.save()
            data = { 'uid': user.id }
            #新增博客信息记录
            try:
                blog = Blog()
                blog.blog_name = user.nickname
                blog.upload_type = 1
                blog.user_id = user.id
                blog.save()
            except Exception as e:
                _errlog('博客信息新增失败',sys._getframe().f_code.co_name)
                _errlog(str(e),sys._getframe().f_code.co_name)
            return _setResult(data=data)
        else:
            _errlog('数据库已存在此账号', sys._getframe().f_code.co_name)
            errorstr = '账号已存在'
            return _setResult(error=errorstr)
    _errlog('无效的接口方法', sys._getframe().f_code.co_name)
    errorstr = '无效的接口方法'
    return _setResult(error=errorstr)
        
#用户登录
def login(request):
    errorstr = None
    data = None
    if request.method == 'POST':
        try:
            name = request.POST.get('login_name',None)
            #pw = request.POST['login_pw'] #这种写法如果没有这个字段会抛出KeyError错误
            pw = request.POST.get('login_pw',None)
            login_type = request.POST.get('login_type','pw')
            agent = request.META.get('HTTP_USER_AGENT',None)
            ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', None)) 
        except Exception as e:
            _errlog(str(e), sys._getframe().f_code.co_name)
            errorstr = str(e)
            return _setResult(error=errorstr,data=data)
        try:
            if login_type == 'pw':
                #如果使用账号密码登录
                user = User.objects.get(login_name=name) #如果找到多条或找不到会抛出错误
            elif login_type == 'sms':
                #短信验证码登录 则账号可以使登录账号或者手机号
                user = User.objects.get(Q(login_name=name) | Q(phone=name))
        except User.DoesNotExist:
            _errlog('数据库无该用户', sys._getframe().f_code.co_name)
            errorstr = '找不到该用户'
            return _setResult(error=errorstr,data=data)
        except Exception as e:
            _errlog(str(e), sys._getframe().f_code.co_name)
            errorstr = str(e)
            return _setResult(error=errorstr,data=data)
        if login_type == 'pw' and user.login_pw != pw:
            errorstr = '密码错误'
            return _setResult(error=errorstr,data=data)
        elif login_type == 'sms':
            #短信验证码登录
            if pw != sms(name):
                errorstr = '密码错误'
                return _setResult(error=errorstr,data=data)

        #默认过期时间为7天后 注意JWT解码需要验证的是UTC时间，因此这里签名用的是UTC
        exptime = datetime.datetime.utcnow() + datetime.timedelta(days=7) #datetime格式 
        #登录时间用的是本地时间
        createtime = time.strftime("%Y-%m-%d %H:%M:%S") #字符串
        payload = {
            'user':user.id,
            'agent':agent, #请求的浏览器信息
            'ip':ip, #请求的ip地址
            'exp':exptime,
            'datetime_create':createtime
        }
        #生成令牌
        encoded_jwt = jwt.encode(payload,settings.SECRET_KEY,algorithm='HS256')
        data = {
            'token':str(encoded_jwt, encoding = "utf8"),
            'user_id':user.id,
            'user_name':user.login_name,
            'user_phone':user.phone,
            'domain':user.domain
        }
        '''
            保存登录令牌
            目前模式为一个用户同时只能在一个设备使用，因为创建时间的关系，每次同IP同设备同个浏览器生成的令牌是不同的
            一个用户对应一个令牌，重登录的话会作废掉之前签发的令牌
        '''
        try:
            ut = UserLogin.objects.get(user_id=user.id)
        except UserLogin.DoesNotExist:
            #用户ID不存在的话就新建
            ut = UserLogin()
            ut.user = user
        ut.datetime_exp = exptime.strftime("%Y-%m-%d %H:%M:%S") #字符串 这个是UTC时间，比实际时间慢8小时
        ut.ip = ip
        ut.agent = agent
        ut.token = str(encoded_jwt, encoding = "utf8")
        ut.datetime_create = createtime
        ut.save()
        return _setResult(error=errorstr,data=data)
    _errlog('无效的接口方法', sys._getframe().f_code.co_name)
    errorstr = '无效的接口方法'
    return _setResult(error=errorstr,data=data)

#用户登出
@auth
def logout(request,user):
    errorstr = None
    data = None
    id = user.id
    if not id:
        _errlog('参数错误',sys._getframe().f_code.co_name)
        errorstr = '参数错误'
        return _setResult(error=errorstr,data=data)
    try:
        ut = UserLogin.objects.get(user_id=id)
        ut.delete()
    except UserLogin.DoesNotExist:
        pass
    except Exception as e:
        _errlog(str(e),sys._getframe().f_code.co_name)
    return _setResult(error=errorstr,data=data)

#获取博客信息 该接口无需验证
def getBlogInfo(request):
    udomain = request.META.get('HTTP_DOMAIN') or request.GET.get('domain',None)
    login = isLogin(request)
    if not udomain:
        _errlog('非法访问',sys._getframe().f_code.co_name)
        errorstr = '非法访问'
        return _setResult(error=errorstr)
    try:
        user = User.objects.get(domain=udomain) #如果找到多条或找不到会抛出错误
    except User.DoesNotExist:
        errorstr = '找不到该用户'
        return _setResult(error=errorstr)
    except Exception as e:
        _errlog(str(e),sys._getframe().f_code.co_name)
        return _setResult(error=str(e))
    try:
        blog = Blog.objects.get(user_id=user.id)
    except Blog.DoesNotExist:
        errorstr = '无此博客信息'
        return _setResult(error=errorstr)
    except Exception as e:
        _errlog(str(e),sys._getframe().f_code.co_name)
        return _setResult(error=str(e))
    data = {
        'id':blog.id,
        'blog_name':blog.blog_name,
        'upload_type':blog.upload_type,
        'seo_desc':blog.seo_desc,
        'seo_keyword':blog.seo_keyword,
        'logo':blog.logo,
        'user_id':blog.user_id,
    }
    #如果用户已登录且上传方式为七牛才会返回七牛参数信息
    if login[0] == True and login[1].id == user.id and blog.upload_type == 2:
        data['qiniu'] = blog.qiniu
    return _setResult(data=data)

#更新博客信息
@auth
def updateBlogInfo(request,u):
    uid = u.id
    try:
        blog = Blog.objects.get(user_id=uid)
    except Blog.DoesNotExist:
        _errlog('无此用户对应博客',sys._getframe().f_code.co_name)
        errorstr = '无此用户对应博客'
        return _setResult(error=errorstr)
    binfo = {
        'blog_name':request.POST.get('blog_name', None),
        'upload_type':request.POST.get('upload_type', None),
        'seo_desc':request.POST.get('seo_desc', None),
        'seo_keyword':request.POST.get('seo_keyword', None),
        'logo':request.POST.get('logo', None),
        'qiniu':request.POST.get('qiniu', None),
    }
    #如果某字段不传，则不修改数据库，若传空值，则会修改为空值
    dl = []
    for key in binfo:
        if binfo[key] == None:
            dl.append(key)
    for i in dl:
        binfo.pop(i)
    blog.__dict__.update(binfo)
    blog.save()
    data = {'uid':blog.id}
    return _setResult(data=data)
        
#获取当前令牌有效用户信息
@auth
def getCurrentUser(request,u):
    #注意不能把整个用户对象返回，因为含有密码等敏感数据
    data = {
        'id':u.id,
        'login_name':u.login_name,
        'nickname':u.nickname,
        'phone':u.phone,
        'avatar':u.avatar,
        'email':u.email,
        'domain':u.domain,
    }
    return _setResult(data=data)

'''
获取用户信息
如果传id，则根据id查询用户
如果无参数，则返回当前域用户信息
'''
def getUserByDomain(request):
    udomain = request.META.get('HTTP_DOMAIN') or request.GET.get('domain',None)
    id = request.GET.get('id',None)
    if not udomain:
        _errlog('非法访问',sys._getframe().f_code.co_name)
        errorstr = '非法访问'
        return _setResult(error=errorstr)
    #根据用户ID或域查找用户
    try:
        if id:
            user = User.objects.get(id=id)
        else:
            user = User.objects.get(domain=udomain) #如果找到多条或找不到会抛出错误
    except User.DoesNotExist:
        errorstr = '找不到该用户'
        return _setResult(error=errorstr)
    except Exception as e:
        _errlog(str(e),sys._getframe().f_code.co_name)
        return _setResult(error=str(e))
    data = {
        'id':user.id,
        'login_name':user.login_name,
        'nickname':user.nickname,
        'phone':user.phone,
        'avatar':user.avatar,
        'email':user.email,
        'domain':user.domain,
        'datetime_reg':user.datetime_reg,
    }
    return _setResult(data=data)

#修改当前用户信息(不能修改密码)
@auth
@require_POST
def updateUser(request,u):
    uid = u.id
    try:
        user = User.objects.get(id=uid)
    except User.DoesNotExist:
        _errlog('找不到用户',sys._getframe().f_code.co_name)
        errorstr = '找不到用户'
        return _setResult(error=errorstr)
    uinfo = {
        'nickname':request.POST.get('nickname', None),
        'email':request.POST.get('email', None),
        'phone':request.POST.get('phone', None),
        'avatar':request.POST.get('avatar', None),
    }
    tvd = {
        'phone':[[uinfo['phone'],11,11],fv.isIntStr, fv.isMinLen, fv.isMaxLen],
        'email':[[uinfo['email'],0,0], fv.isEmail]
    }
    dk = []
    for key in uinfo:
        if uinfo[key] != None and uinfo[key] != '':
            if key in tvd:
                vd = { 'check':tvd[key] }
                if fv.validator(validatdict = vd)[0] is False:
                    errorstr = fv.validator(validatdict = vd)[1]
                    _errlog(errorstr, sys._getframe().f_code.co_name)
                    code = 810100
                    return _setResult(error=errorstr,code=code)
        else:
            #如果某用户信息不传值或值为空，则不修改数据库
            dk.append(key)
    for i in dk:
        uinfo.pop(i)
    user.__dict__.update(uinfo) #用户模型是对象，不能用类似user[key]的方式赋值，只能用字典来修改
    user.save()
    data = {'uid':user.id}
    return _setResult(data=data)

#修改当前用户密码
@auth
@require_POST
def updateUserPw(request,u):
    uid = u.id
    try:
        user = User.objects.get(id=uid)
    except User.DoesNotExist:
        _errlog('找不到用户',sys._getframe().f_code.co_name)
        errorstr = '找不到用户'
        return _setResult(error=errorstr)
    pw_old = request.POST.get('pw_old', None)
    pw_new = request.POST.get('pw_new', None)
    if pw_old != user.login_pw:
        _errlog('旧密码错误',sys._getframe().f_code.co_name)
        errorstr = '旧密码错误'
        code = 810100
        return _setResult(error=errorstr,code=code)
    vd = {'loginpw':[[pw_new, 6],fv.isPW],}
    if fv.validator(validatdict = vd)[0] is False:
        errorstr = fv.validator(validatdict = vd)[1]
        _errlog(errorstr, sys._getframe().f_code.co_name)
        code = 810100
        return _setResult(error=errorstr,code=code)
    user.login_pw = pw_new
    user.save()
    return _setResult()

'''
获取用户的所有的文章，按发表日期排序
默认获取对应用户（域名）的文章，该字段通过HEADER或者query参数传递
注意登录与未登录用户获取到的文章范围不一样
'''
def getArticleList(request):
    udomain = request.META.get('HTTP_DOMAIN') or request.GET.get('domain',None)
    mode = request.GET.get('mode', None)
    login = isLogin(request)
    if mode == 'admin':
        #如果传此参数，则查询的是当前登录用户的
        if login[0] == True:
            uid = login[1].id
        else:
            _errlog('无此操作权限',sys._getframe().f_code.co_name)
            errorstr = '无此操作权限'
            return _setResult(error=errorstr)
    else:       
        if not udomain:
            _errlog('非法访问',sys._getframe().f_code.co_name)
            errorstr = '非法访问'
            return _setResult(error=errorstr)
        #根据用户域查找用户
        try:
            user = User.objects.get(domain=udomain) #如果找到多条或找不到会抛出错误
        except User.DoesNotExist:
            errorstr = '找不到该用户'
            return _setResult(error=errorstr)
        except Exception as e:
            _errlog(str(e),sys._getframe().f_code.co_name)
            return _setResult(error=str(e))
        uid = user.id
    state = None
    #如果该用户已经登录 则可以查找草稿和公开文章，否则只能查找公开文章
    if login[0] == True and login[1].id == uid:
        state = request.GET.get('state', None)
    else:
        state = 1
    search_obj = {
        'state':state,
        'title':request.GET.get('title', None),
        'category_id':request.GET.get('category', None),
        'tag':request.GET.get('tag', None),
        'datetime_start':request.GET.get('datetime_start', None), #要字符串格式
        'datetime_end':request.GET.get('datetime_end', None),
        'page_index':request.GET.get('page_index', None),
        'page_size':request.GET.get('page_size', None),
        'key':request.GET.get('key', None),
    }
    dk = []
    for key in search_obj:
        if search_obj[key] == None or search_obj[key] == '':
            dk.append(key)
    for i in dk:
        search_obj.pop(i)
    #开始检索
    #用户的所有文章(草稿或者公开)
    try:
        q = Article.objects.filter(user_id=uid)
        if 'state' in search_obj:
            q = q.filter(state=search_obj['state'])
        if 'category_id' in search_obj:
            print('类别')
            q = q.filter(category_id=search_obj['category_id'])
        if 'datetime_start' in search_obj:
            print('开始日期')
            ct = datetime.datetime.strptime(search_obj['datetime_start'],'%Y-%m-%d')
            q = q.filter(datetime_create__gte = ct)
        if 'datetime_end' in search_obj:
            print('结束日期')
            ct = datetime.datetime.strptime(search_obj['datetime_end'],'%Y-%m-%d')
            q = q.filter(datetime_create__lte = ct)
        if 'title' in search_obj:
            print('标题')
            q = q.filter(title__contains = search_obj['title'])
        if 'tag' in search_obj:
            print('标签')
            tag = search_obj['tag'].replace(',', '') #这里暂只能查询单个tag
            q = q.filter(tag__contains = tag)
        if 'key' in search_obj:
            #目前关键字仅支持标题搜索
            print('关键字')
            q = q.filter(title__contains = search_obj['key'])
        #按日期倒序
        q = q.order_by('-datetime_create')
        count = len(q)
        if 'page_index' in search_obj and 'page_size' in search_obj:
            paginator = Paginator(q, search_obj['page_size'])
            q = paginator.page(search_obj['page_index']) #注意这里q不是QuerySet对象了
        #设置返回的列表数据
        article_list = []
        for i in q:
            json_dict = model_to_dict(i)
            json_dict.pop('browse_ips')
            if i.category:
                json_dict['category_name'] = i.category.label
            else:
                json_dict['category_name'] = ''
            #json_dict.pop('thumb_users')
            article_list.append(json_dict)
        #查找置顶文章ID（该文章需要发布后才有效）
        res_articles = []
        try:
            #获取用户数据视图中的第一条数据（该视图应该只有一条数据）
            q2 = ArticleTop.objects.filter(user_id=uid).first()
            if q2:
                att = model_to_dict(q2)
                top_id = att['article_id'] #置顶ID
                #找到置顶文章对象提出来，然后将剩下的放到一个列表里，最后把置顶插入列表第一位
                for j in article_list:
                    if j['id'] == top_id:
                        top_article = j
                    else:
                        res_articles.append(j)
                res_articles.insert(0,top_article)
        except Exception as e:
            _errlog(str(e),sys._getframe().f_code.co_name)
        data = {
            'list':[],
            'count':count,
        }
        if len(res_articles) > 0:
            data['list'] = res_articles
        else:
            data['list'] = article_list
    except Exception as e:
        _errlog(e,sys._getframe().f_code.co_name)
        return  _setResult(error=str(e))
    return  _setResult(data=data)

'''
根据文章id获取文章信息（不需验证）
仅获取对应用户（域名）的文章，该字段通过HEADER或者query参数传递
如果文章为草稿，需要核对一下用户是否当前登录，否则不返回
'''
def getArticleInfo(request):
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', None))
    udomain = request.META.get('HTTP_DOMAIN') or request.GET.get('domain',None)
    if not udomain:
        _errlog('非法访问',sys._getframe().f_code.co_name)
        errorstr = '非法访问'
        return _setResult(error=errorstr)
    try:
        user = User.objects.get(domain=udomain) #如果找到多条或找不到会抛出错误
    except User.DoesNotExist:
        errorstr = '找不到该用户'
        return _setResult(error=errorstr)
    except Exception as e:
        print(e)
        return _setResult(error=str(e))
    uid = user.id
    aid = request.GET.get('id', None) or request.POST.get('id', None)
    try:
        at = Article.objects.get(id=aid,user_id=uid)
    except Article.DoesNotExist:
        _errlog('文章不存在',sys._getframe().f_code.co_name)
        errorstr = '文章不存在'
        return _setResult(error=errorstr)
    #仅当前登录用户可以查看自己的草稿文章
    if at.state == 0:
        login = isLogin(request)
        if not (login[0] == True and login[1].id == at.user_id):
            _errlog('仅当前登录用户可以查看自己的草稿文章',sys._getframe().f_code.co_name)
            errorstr = '该文章无法查看'
            return _setResult(error=errorstr)
    #记录浏览ip
    abi = []
    if at.browse_ips:
        abi = at.browse_ips.split(',')
    if not str(ip) in abi:
        abi.append(str(ip))
        at.browse_ips = ','.join([str(i) for i in abi])
        at.num_browse += 1
        at.save()
    data = model_to_dict(at)
    data.pop('thumb_users')
    data.pop('browse_ips')
    if at.category:
        data['category_name'] = at.category.label
    return _setResult(data=data)

#获取置顶的文章?
def getTopArticle(request):
    udomain = request.META.get('HTTP_DOMAIN') or request.GET.get('domain',None)
    if not udomain:
        _errlog('非法访问',sys._getframe().f_code.co_name)
        errorstr = '非法访问'
        return _setResult(error=errorstr)
    #根据用户域查找用户
    try:
        user = User.objects.get(domain=udomain) #如果找到多条或找不到会抛出错误
    except User.DoesNotExist:
        errorstr = '找不到该用户'
        return _setResult(error=errorstr)
    except Exception as e:
        print(e)
        return _setResult(error=str(e))
    uid = user.id
    try:
        #获取视图中的第一条数据（该视图应该只有一条数据）
        q = ArticleTop.objects.all().first()
        att = model_to_dict(q)
    except Exception as e:
        _errlog(e,sys._getframe().f_code.co_name)
    return

#获取某个用户的所有文章标签（不需验证）
def getArticleTag(request):
    udomain = request.META.get('HTTP_DOMAIN') or request.GET.get('domain',None)
    if not udomain:
        _errlog('非法访问',sys._getframe().f_code.co_name)
        errorstr = '非法访问'
        return _setResult(error=errorstr)
    #根据用户域查找用户
    try:
        user = User.objects.get(domain=udomain) #如果找到多条或找不到会抛出错误
    except User.DoesNotExist:
        errorstr = '找不到该用户'
        return _setResult(error=errorstr)
    except Exception as e:
        print(e)
        return _setResult(error=str(e))
    uid = user.id
    try:
        q = Article.objects.filter(user_id=uid,state=1)
        q = q.filter(~Q(tag = ''))
        tagstr = ''
        for i in q:
            tagstr += i.tag + ','
        #分割成数组
        tag = tagstr.split(",")
        #去空
        tag = list(filter(None, tag))
        #去重
        data = { 'list':list(set(tag)) }
    except Exception as e:
        print(e)
        return _setResult(error=str(e))
    return _setResult(data=data)

'''
当前用户新增或编辑文章
新增时必传文章标题
编辑时可单独修改某个字段
'''
@auth
@require_POST
def updateArticle(request,u):
    aid = request.POST.get('id', None)
    ainfo = {
        'title':request.POST.get('title', None),
        'desc':request.POST.get('desc', None),
        'content':request.POST.get('content', None),
        'content_html':request.POST.get('content_html', None),
        'tag':request.POST.get('tag', None),
        'state':request.POST.get('state', None),
        'category_id':request.POST.get('category', None),
        'user_id':u.id,
        'is_top':request.POST.get('is_top', None),
        'is_comment':request.POST.get('is_comment', None),
    }
    vd = {
        'title':[[ainfo['title']],fv.isNotNull],
    }
    if not aid or str(aid) == str(0):
        #新增
        if fv.validator(validatdict = vd)[0] is False:
            errorstr = '标题不能为空'
            _errlog(fv.validator(validatdict = vd)[1], sys._getframe().f_code.co_name)
            code = 810100
            return _setResult(error=errorstr,code=code)
        ainfo['datetime_create'] = time.strftime("%Y-%m-%d %H:%M:%S")
        ainfo['num_update'] = 0
        ainfo['num_browse'] = 0
        ainfo['num_thumb'] = 0
        ainfo['num_comment'] = 0
        ainfo['is_top'] = ainfo['is_top'] or False
        ainfo['is_comment'] = ainfo['is_comment'] or True
        ainfo['state'] = ainfo['state'] or 0
        at = Article()
    else:
        #编辑
        try:
            at = Article.objects.get(id=aid,user_id=u.id)
        except Article.DoesNotExist:
            _errlog('文章不存在',sys._getframe().f_code.co_name)
            errorstr = '文章不存在'
            return _setResult(error=errorstr)
        #如果是编辑模式，无值的字段不进行更新
        dk = []
        for key in ainfo:
            if ainfo[key] == None or ainfo[key] == '':
                dk.append(key)
        for i in dk:
            ainfo.pop(i)
        ainfo['datetime_update'] = time.strftime("%Y-%m-%d %H:%M:%S")
        ainfo['num_update'] = int(at.num_update) + 1
    #如果置顶为True,则记录置顶时间
    if 'is_top' in ainfo and ainfo['is_top']:
        ainfo['datetime_top'] = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        at.__dict__.update(ainfo) 
        at.save()
    except Exception as e:
        _errlog(str(e),sys._getframe().f_code.co_name)
        errorstr = str(e)
        return _setResult(error=errorstr)
    data = { 'aid':at.id }
    return _setResult(data=data)

#当前用户删除自己的文章
@auth
@require_POST
def delArticle(request,u):
    uid = u.id
    aid = request.POST.get('id', None)
    if not aid:
        _errlog('缺少文章ID',sys._getframe().f_code.co_name)
        errorstr = '缺少参数'
        return _setResult(error=errorstr)
    try:
        at = Article.objects.get(id=aid,user_id=u.id)
    except Article.DoesNotExist:
        _errlog('文章不存在',sys._getframe().f_code.co_name)
        errorstr = '文章不存在'
        return _setResult(error=errorstr)
    #删除文章的所有评论
    try:
        ct = Comment.objects.filter(article_id=aid)
        ct.delete()
    except Exception as e:
        _errlog('删除文章相关联评论失败',sys._getframe().f_code.co_name)
        _errlog(e,sys._getframe().f_code.co_name)
        return _setResult()
    at.delete()
    return _setResult()

#当前用户点赞某文章
@auth
@require_POST
def thumbArticle(request,u):
    data = None
    aid = request.POST.get('id', None)
    op = request.POST.get('op', None)
    try:
        at = Article.objects.get(id=aid)
    except Article.DoesNotExist:
        _errlog('文章不存在',sys._getframe().f_code.co_name)
        errorstr = '文章不存在'
        return _setResult(error=errorstr)
    tu = []
    if at.thumb_users:
        tu = at.thumb_users.split(',')
    if str(op) == str(1):
        if str(u.id) in tu:
            return _setResult()
        else:
            tu.append(str(u.id))
            at.thumb_users = ','.join([str(i) for i in tu])
            at.num_thumb += 1
            data = '点赞成功'
    elif str(op) == str(0):
        if str(u.id) in tu:
            tu.remove(str(u.id))
            at.thumb_users = ','.join([str(i) for i in tu])
            if at.num_thumb >= 1:
                at.num_thumb -= 1
            data = '取消点赞成功'
        else:
            return _setResult()
    at.save()
    return _setResult(data=data)

#增加某文章浏览数
def browseArticle(request):
    aid = request.GET.get('id', None) or request.POST.get('id', None)
    try:
        at = Article.objects.get(id=aid)
    except Article.DoesNotExist:
        _errlog('文章不存在',sys._getframe().f_code.co_name)
        errorstr = '文章不存在'
        return _setResult(error=errorstr)
    at.num_browse += 1
    at.save()
    return _setResult()

'''
获取用户的分类列表（不需验证）
仅获取对应用户（域名）的分类，该字段通过HEADER或者query参数传递
'''
def getCategoryByDomain(request):
    udomain = request.META.get('HTTP_DOMAIN') or request.GET.get('domain',None)
    try:
        user = User.objects.get(domain=udomain) #如果找到多条或找不到会抛出错误
    except User.DoesNotExist:
        errorstr = '找不到该用户'
        return _setResult(error=errorstr)
    except Exception as e:
        print(e)
        return _setResult(error=str(e))
    uid = user.id
    try:
        category = Category.objects.filter(user_id=uid).order_by('index')
    except:
        _errlog('查找类别出错',sys._getframe().f_code.co_name)
        errorstr = '查找类别出错'
        return _setResult(error=errorstr)
    res_l = []
    for i in category:
        json_dict = model_to_dict(i)
        num = Article.objects.filter(user_id=uid,category_id=i.id,state=1).count()
        json_dict['article_num'] = num
        res_l.append(json_dict)
    data = {
        'list':res_l,
    }
    return  _setResult(data=data)

#获取当前登录用户的分类列表
@auth
def getCategoryByUser(request,u):
    uid = u.id
    try:
        category = Category.objects.filter(user_id=uid).order_by('index')
    except:
        _errlog('查找类别出错',sys._getframe().f_code.co_name)
        errorstr = '查找类别出错'
        return _setResult(error=errorstr)
    res_l = []
    for i in category:
        json_dict = model_to_dict(i)
        num = Article.objects.filter(user_id=uid,category_id=i.id).count()
        json_dict['article_num'] = num
        res_l.append(json_dict)
    data = {
        'list':res_l,
    }
    return  _setResult(data=data)

#新增或编辑分类(每个用户有自己的分类树)
#数据库数据结构是树形，目前使用的只有一级，即目前所有类别都是根级
@auth
@require_POST
def updateCategory(request,u):
    uid = u.id
    cid = request.POST.get('id', None)
    label = request.POST.get('label', None) #必传
    pid = request.POST.get('pid', None)
    if label == None or label == '':
        _errlog('分类名称不能为空',sys._getframe().f_code.co_name)
        errorstr = '分类名称不能为空'
        code = 810100
        return _setResult(error=errorstr,code=code)
    if pid:
        try:
            pcategory = Category.objects.get(id=pid,user_id=uid)
        except Category.DoesNotExist:
            _errlog('父分类不存在',sys._getframe().f_code.co_name)
            errorstr = '父分类不存在'
            code = 810100
            return _setResult(error=errorstr,code=code)
        else:
            level = int(pcategory.level) + 1
            #trace = pcategory.trace + cid + '-'
    else:
        level = 0
        #trace = cid + '-'
    if not cid or str(cid) == str(0):
        #新增
        category = Category()
        category.user_id = uid
    else:
        #编辑
        try:
            category = Category.objects.get(id=cid,user_id=uid)
        except Category.DoesNotExist:
            _errlog('分类不存在',sys._getframe().f_code.co_name)
            errorstr = '分类不存在'
            return _setResult(error=errorstr)
    category.pid = pid
    category.label = label
    category.level = level
    category.save()
    #先保存拿到cid，然后再次保存存上trace字段
    if pid:
        trace = pcategory.trace + str(category.id) + '-'
    else:
        trace = str(category.id) + '-'
    category.trace = trace
    category.save()
    data = { 'cid':category.id }
    return _setResult(data=data)

@auth
@require_POST
def delCategory(request,u):
    #删除文章类别
    uid = u.id
    cid = request.POST.get('id', None)
    if not cid:
        _errlog('缺少参数',sys._getframe().f_code.co_name)
        errorstr = '缺少参数'
        return _setResult(error=errorstr)
    try:
        category = Category.objects.get(id=cid,user_id=uid)
    except Category.DoesNotExist:
        _errlog('无此类别',sys._getframe().f_code.co_name)
        errorstr = '无此类别'
        return _setResult(error=errorstr)
    except Exception as e:
        _errlog(str(e), sys._getframe().f_code.co_name)
        errorstr = str(e)
        return _setResult(error=errorstr,data=data)
    category.delete()
    #将类别下所有文章的类别字段置为空
    try:
        q = Article.objects.filter(user_id=uid,category_id=cid)
        for i in q:
            i.category_id = None
            i.save()
    except Exception as e:
        _errlog(str(e), sys._getframe().f_code.co_name)
        errorstr = str(e)
        return _setResult(error=errorstr,data=data)
    return _setResult()

#分类排序
@auth
@require_POST
def sortCategory(request,u):
    uid = u.id
    slstr = request.POST.get('sort_data', None)
    if not slstr:
        errorstr = '缺少排序参数'
        return _setResult(error=errorstr)
    sort_list = ast.literal_eval(slstr)
    q = Category.objects.filter(user_id=uid)
    if len(sort_list) != len(q):
        errorstr = '排序参数不正确'
        return _setResult(error=errorstr)
    try:
        for i in sort_list:
            c = q.get(id=i['id'])
            c.index = i['index']
            c.save()
    except Exception as e:
        _errlog('更新分类排序出错',sys._getframe().f_code.co_name)
        _errlog(str(e),sys._getframe().f_code.co_name)
        errorstr = '更新分类排序出错'
        return _setResult(error=errorstr)
    return _setResult()
    

#本地上传文件
@auth
@require_POST
def uploadFile(request,u):
    uid = u.id
    file = request.FILES.get('file',None)
    fsu = request.POST.get('suffix', None)
    purpose = request.POST.get('purpose', None)
    #图片保存在upload文件夹中用户ID所属文件夹内
    furl = file_url + str(uid)
    path = os.path.abspath(os.path.join(settings.BASE_DIR, furl))
    if not os.path.exists(path):
        os.makedirs(furl)
    #文件重命名
    suffix = file.name.split('.')[1] or fsu
    fn = genID() + '.' + suffix
    #保存文件
    path = os.path.join(path,fn)
    print(path)
    f = open(path, 'wb')
    for chunk in file.chunks():
        f.write(chunk)
    f.close()
    data = {
        'name':file.name,
        'url':file_access_prefix + str(uid)  + '/' + fn,
    }
    if purpose and purpose == 'avatar':
        try:
            user = User.objects.get(id=uid)
        except User.DoesNotExist:
            _errlog('用户不存在，保存头像失败',sys._getframe().f_code.co_name)
        user.avatar = file_access_prefix + str(uid)  + '/' + fn
        user.save()
    if purpose  and purpose == 'logo':
        pass
    return _setResult(data=data)

#批量编辑文章单个属性
@auth
@require_POST
def editArticleMult(request,u):
    props = ['tag','state','category_id','is_comment'] #文章的可编辑属性字段
    aids = request.POST.get('aids', None) #需要批量的文章ID
    prop = request.POST.get('prop', None) #需要更改的属性字段，对应数据库字段
    value = request.POST.get('value', None) #更改的值
    if not aids:
        _errlog('缺少参数',sys._getframe().f_code.co_name)
        errorstr = '缺少参数'
        return _setResult(error=errorstr)
    if not prop in props:
        _errlog('【' + str(prop) + '】属性不支持批量修改',sys._getframe().f_code.co_name)
        errorstr = '【' + str(prop) + '】属性不支持批量修改'
        return _setResult(error=errorstr)
    if aids != 'all':
        try:
            info = {}
            info[prop] = value
            info['datetime_update'] = time.strftime("%Y-%m-%d %H:%M:%S")
            info['num_update'] = F('num_update') + 1
            Article.objects.extra(where=["user_id=" + str(u.id), "id IN ("+ aids +")"]).update(**info)
        except Exception as e:
            _errlog('更新文章属性出错-' + str(prop),sys._getframe().f_code.co_name)
            _errlog(str(e),sys._getframe().f_code.co_name)
            errorstr = '更新文章属性出错'
            return _setResult(error=errorstr)
    return _setResult()

'''
当前用户批量删除文章
如果传ID列表字符就会按ID删除，如果不传ID列表就会按传的日期段删除
'''
@auth
@require_POST
def delArticleMult(request,u):
    aids = request.POST.get('aids', None) #需要批量的文章ID
    date_start = request.POST.get('date_start', None)
    date_end = request.POST.get('date_end', None)
    if not date_start and not date_end and not aids:
        _errlog('缺少参数',sys._getframe().f_code.co_name)
        errorstr = '缺少参数'
        return _setResult(error=errorstr)
    elif not aids:
        if (not date_start) or (not date_end):
            _errlog('缺少参数',sys._getframe().f_code.co_name)
            errorstr = '缺少参数'
            return _setResult(error=errorstr)
    if aids:
        try:
            Article.objects.extra(where=["user_id=" + str(u.id), "id IN ("+ aids +")"]).delete()
            #注意这里还要过滤一下该文章是否是当前用户的文章
            Comment.objects.extra(where=["article_id IN ("+ aids +")"]).delete()
        except Exception as e:
            _errlog('批量删除文章出错',sys._getframe().f_code.co_name)
            _errlog(str(e),sys._getframe().f_code.co_name)
            errorstr = '批量删除文章出错'
            return _setResult(error=errorstr)
    else:
        try:
            ds = datetime.datetime.strptime(date_start,'%Y-%m-%d')
            de = datetime.datetime.strptime(date_end,'%Y-%m-%d')
            q = Article.objects.filter(user_id=u.id,datetime_create__range=(ds,de))
            article_del = ''
            for i in q:
                article_del += str(i.id) + ','
            q.delete()
            if article_del:
                Comment.objects.extra(where=["article_id IN ("+ article_del[:-1] +")"]).delete()
        except Exception as e:
            _errlog('批量删除文章出错',sys._getframe().f_code.co_name)
            _errlog(str(e),sys._getframe().f_code.co_name)
            errorstr = '批量删除文章出错'
            return _setResult(error=errorstr)
    return _setResult()

#获取某个文章的评论列表
def getCommentListByArticle(request):
    cminfo = {
        'aid':request.GET.get('aid', None),
        'page_index':request.GET.get('page_index', None),
        'page_size':request.GET.get('page_size', None),
    }
    if not cminfo['aid']:
        errorstr = '缺少文章id'
        _errlog('缺少文章ID', sys._getframe().f_code.co_name)
        code = 810100
        return _setResult(error=errorstr,code=code)
    try:
        q = Comment.objects.filter(article_id=cminfo['aid'])
        #按日期倒序
        q = q.order_by('-datetime_create')
        count = len(q)
        # if 'page_index' in cminfo and 'page_size' in cminfo:
        #     paginator = Paginator(q, cminfo['page_size'])
        #     q = paginator.page(cminfo['page_index']) #注意这里q不是QuerySet对象了
        res_l = []
        for i in q:
            json_dict = model_to_dict(i)
            res_l.append(json_dict)
        data = {
            'list':res_l,
            'count':count,
        }
    except Exception as e:
        _errlog(e,sys._getframe().f_code.co_name)
        errorstr = '查找评论出错'
        return _setResult(error=errorstr)
    return  _setResult(data=data)

'''
新增文章评论
不需登录
客户端如果不传某字段，那request.POST.get('***', None)的值为None
如果传的字段为空字符串''，则值也会为空字符串
如果传的字段为null值，则值为空字符串
'''
def addComment(request):
    cminfo = {
        'article_id':request.POST.get('aid', None),
        'content':request.POST.get('content', None),
        'to_comment_id':request.POST.get('to_comment_id', None),
        'from_user_id':None,
        'from_user_name':request.POST.get('from_user_name',None),
        'datetime_create':time.strftime("%Y-%m-%d %H:%M:%S")
    }
    if not cminfo['article_id']:
        errorstr = '缺少文章id'
        _errlog('缺少文章ID', sys._getframe().f_code.co_name)
        code = 810100
        return _setResult(error=errorstr,code=code)
    if not cminfo['content']:
        errorstr = '评论内容不能为空'
        _errlog('评论内容不能为空', sys._getframe().f_code.co_name)
        code = 810100
        return _setResult(error=errorstr,code=code)
    try:
        at = Article.objects.get(id=cminfo['article_id'])
    except Article.DoesNotExist:
        _errlog('文章不存在',sys._getframe().f_code.co_name)
        errorstr = '文章不存在'
        return _setResult(error=errorstr)
    login = isLogin(request)
    if login[0] == True:
        user = login[1]
        cminfo['from_user_id'] = user.id
        cminfo['from_user_name'] = user.nickname
    else:
        if not cminfo['from_user_name']:
            cminfo['from_user_name'] = '路人('+ genID(36) +')'
    try:
        cmt = Comment()
        cmt.__dict__.update(cminfo) 
        cmt.save()
    except Exception as e:
        _errlog(str(e),sys._getframe().f_code.co_name)
        errorstr = str(e)
        return _setResult(error=errorstr)
    #修改文章对应评论数
    try:
        at.num_comment += 1
        at.save()
    except Exception as e:
        _errlog('保存文章评论数出错',sys._getframe().f_code.co_name)
        _errlog(str(e),sys._getframe().f_code.co_name)
    data = { 'cmid':cmt.id }
    return _setResult(data=data)

@auth
@require_POST
def delComment(request,u):
    #文章作者删除本人单条文章评论
    cmid = request.POST.get('id', None)
    if not cmid:
        _errlog('缺少评论ID',sys._getframe().f_code.co_name)
        errorstr = '缺少参数'
        return _setResult(error=errorstr)
    try:
        ct = Comment.objects.get(id=cmid)
    except Comment.DoesNotExist:
        _errlog('评论不存在',sys._getframe().f_code.co_name)
        errorstr = '评论不存在'
        return _setResult(error=errorstr)
    aid = ct.article_id
    try:
        at = Article.objects.get(id=aid,user_id=u.id)
    except Article.DoesNotExist:
        _errlog('仅能删除当前用户的文章评论',sys._getframe().f_code.co_name)
        errorstr = '仅能删除当前用户的文章评论'
        return _setResult(error=errorstr)
    ct.delete()
    #修改文章对应评论数
    try:
        at.num_comment -= 1
        at.save()
    except Exception as e:
        _errlog('保存文章评论数出错',sys._getframe().f_code.co_name)
        _errlog(str(e),sys._getframe().f_code.co_name)
    return _setResult()

@auth
@require_POST
def delCommentByArticle(request,u):
    #文章作者删除本人某篇文章的所有评论
    aid = request.POST.get('aid', None)
    try:
        at = Article.objects.get(id=aid,user_id=u.id)
    except Article.DoesNotExist:
        _errlog('仅能删除当前用户的文章评论',sys._getframe().f_code.co_name)
        errorstr = '仅能删除当前用户的文章评论'
        return _setResult(error=errorstr)
    ct = Comment.objects.filter(article_id=aid)
    ct.delete()
    #修改文章对应评论数
    try:
        at.num_comment = 0
        at.save()
    except Exception as e:
        _errlog('保存文章评论数出错',sys._getframe().f_code.co_name)
        _errlog(str(e),sys._getframe().f_code.co_name)
    return _setResult()

def delCommentMult(request):
    #文章作者批量删除本人文章评论
    return  

'''
导出文章数据到EXCEL
''' 
@auth
@require_POST
def exportExcel(request,u):
    year = request.POST.get('year', None)
    if not year:
        _errlog('缺少年份参数',sys._getframe().f_code.co_name)
        errorstr = '缺少参数'
        return _setResult(error=errorstr)
    year = int(year)
    st = datetime.datetime.strptime(str(year) + '-1-1','%Y-%m-%d')
    et = datetime.datetime.strptime(str(year+1) + '-1-1','%Y-%m-%d')
    try:
        q = Article.objects.filter(user_id=u.id,datetime_create__gte = st,datetime_create__lt = et)
    except Exception as e:
        _errlog('获取数据出错',sys._getframe().f_code.co_name)
        _errlog(str(e),sys._getframe().f_code.co_name)
        errorstr = '获取数据出错'
        return _setResult(error=errorstr)
    article_list = []
    for i in q:
        json_dict = model_to_dict(i)
        article_list.append(json_dict)
    filename = str(year) + '.xls'
    # 创建一个workbook 设置编码
    workbook = xlwt.Workbook(encoding = 'utf-8')
    # 创建一个worksheet
    worksheet = workbook.add_sheet('sheet1')
    dateFormat = xlwt.XFStyle()
    dateFormat.num_format_str = 'yyyy/mm/dd'
    try:
        for i in article_list:
            ti = article_list.index(i) #行索引
            if ti == 0:
                #第一行的标题
                title = ['序号','标题','内容','日期']
                for x in title:
                    worksheet.write(ti,title.index(x),x)
            else:
                label = ['index','title','content_html','datetime_create']
                for j in label:
                    li = label.index(j)
                    #第一列的序号
                    if label.index(j) == 0:
                        worksheet.write(ti,li,ti)
                    #第四列的日期
                    elif label.index(j) == 3:
                        worksheet.write(ti,li,article_list[ti][j],dateFormat) 
                    else:
                        worksheet.write(ti,li,article_list[ti][j])      
        sio = BytesIO()
        workbook.save(sio)
    except Exception as e:
        _errlog(str(e),sys._getframe().f_code.co_name)
        errorstr = str(e)
        return _setResult(error=errorstr)
    response = HttpResponse(sio.getvalue())
    response['Content-Type']='application/octet-stream'
    response['Content-Disposition'] = 'attachment; filename=' + filename
    return response
    