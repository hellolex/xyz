import os
from django.urls import path, re_path
from django.views.static import serve
from django.conf import settings
from . import views
from django.views.generic.base import TemplateView

urlpatterns = [
    
    #上传文件
    path('file/upload/', views.uploadFile, name='upload-file'),
    
    #获取当前用户信息
    path('auth/', views.getCurrentUser, name='get-current-user'),

    #登录 POST
    path('login/', views.login, name='login'),

    #登出 POST
    path('logout/', views.logout, name='logout'),

    #注册 POST
    path('reg/', views.reg, name='reg'),

    #获取博客信息
    path('blog/', views.getBlogInfo, name='get-blog-info'),

    #修改博客信息
    path('blog/update/', views.updateBlogInfo, name='update-blog-info'),

    #修改用户信息 POST
    path('user/update/', views.updateUser, name='update-user'),

    #修改用户密码 POST
    path('user/update-pw/', views.updateUserPw, name='update-user-pw'),
    
    #编辑文章 POST
    path('article/edit/', views.updateArticle, name='edit-article'),

    #批量编辑文章属性 POST
    path('article/edit-mult/', views.editArticleMult, name='edit-article-mult'),

    #获取文章集 GET
    path('articles/', views.getArticleList, name='articles'),

    #获取文章信息 GET
    path('article/', views.getArticleInfo, name='article'),

    #删除文章 POST
    path('article/del/', views.delArticle, name='del-article'),

    #批量删除文章 POST
    path('article/del-mult/', views.delArticleMult, name='del-article-mult'),

    #点赞文章 POST
    path('article/thumb/', views.thumbArticle, name='thumb-article'),

    #编辑文章分类 POST
    path('category/update/', views.updateCategory, name='update-category'),

    #删除文章类别 POST
    path('category/del/', views.delCategory, name='del-category'),

    #排序文章类别 POST
    path('category/sort/', views.sortCategory, name='sort-category'),

    #获取对应用户域的文章分类 GET
    path('category-domain/', views.getCategoryByDomain, name='get-category-by-domain'),

    #获取当前登录用户的文章分类
    path('category/', views.getCategoryByUser, name='get-category-by-user'),

    #新增文章评论 POST
    path('comment/add/', views.addComment, name='add-comment'),

    #获取文章的评论列表
    path('comment/', views.getCommentListByArticle, name='get-comment-by-article'),

    #删除单个文章评论 POST
    path('comment/del/', views.delComment, name='del-comment'),

    #删除文章全部评论 POST
    path('comment/del-article/', views.delCommentByArticle, name='del-article-comment'),

    #获取对应域的用户信息
    path('user-domain/', views.getUserByDomain, name='get-user-domain'),

    #导出文章
    path('export-article/', views.exportExcel, name='export-article'),

    #获取单个用户的所有文章tag
    path('article-tag/', views.getArticleTag, name='get-article-tag'),
    
]

handler404 = views.page_not_found