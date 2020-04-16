from django.db import models


class User(models.Model):
    login_name = models.CharField(unique=True, max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    login_pw = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    avatar = models.CharField(max_length=255, blank=True, null=True)
    datetime_reg = models.DateTimeField(blank=True, null=True)
    nickname = models.CharField(max_length=255, blank=True, null=True)
    login_type = models.CharField(max_length=255, blank=True, null=True)
    domain = models.CharField(unique=True, max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'USER'

    def __str__(self):
        return self.login_name

class Category(models.Model):
    user = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)
    pid = models.IntegerField(blank=True, null=True)
    label = models.CharField(max_length=255, blank=True, null=True)
    level = models.CharField(max_length=255, blank=True, null=True)
    trace = models.CharField(max_length=255, blank=True, null=True)
    index = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'CATEGORY'

    def __str__(self):
        return self.label

class Article(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    desc = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    content_html = models.TextField(blank=True, null=True)
    user = models.ForeignKey('User', models.DO_NOTHING)
    datetime_create = models.DateTimeField(blank=True, null=True)
    num_browse = models.IntegerField(blank=True, null=True)
    num_thumb = models.IntegerField(blank=True, null=True)
    num_comment = models.IntegerField(blank=True, null=True)
    category = models.ForeignKey('Category', models.DO_NOTHING, blank=True, null=True)
    tag = models.CharField(max_length=255, blank=True, null=True)
    state = models.IntegerField(blank=True, null=True)
    datetime_update = models.DateTimeField(blank=True, null=True)
    num_update = models.IntegerField(blank=True, null=True)
    is_top = models.IntegerField(blank=True, null=True)
    is_comment = models.IntegerField(blank=True, null=True)
    datetime_top = models.DateTimeField(blank=True, null=True)
    thumb_users = models.TextField(blank=True, null=True)
    browse_ips = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'ARTICLE'

    def __str__(self):
        return self.title

class UserLogin(models.Model):
    user = models.ForeignKey(User, models.DO_NOTHING, blank=True, null=True)
    token = models.TextField(blank=True, null=True)
    datetime_create = models.DateTimeField(blank=True, null=True)
    ip = models.CharField(max_length=255, blank=True, null=True)
    agent = models.CharField(max_length=255, blank=True, null=True)
    datetime_exp = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'USER_LOGIN'

    def __str__(self):
        return self.user

class Comment(models.Model):
    content = models.TextField(blank=True, null=True)
    article_id = models.IntegerField()
    datetime_create = models.DateTimeField(blank=True, null=True)
    to_comment_id = models.IntegerField(blank=True, null=True)
    from_user_id = models.IntegerField(blank=True, null=True)
    from_user_name = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'comment'
    
    def __str__(self):
        return self.comment

class Blog(models.Model):
    blog_name = models.CharField(max_length=255, blank=True, null=True)
    upload_type = models.IntegerField(blank=True, null=True)
    seo_desc = models.CharField(max_length=255, blank=True, null=True)
    seo_keyword = models.CharField(max_length=255, blank=True, null=True)
    logo = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey('User', models.DO_NOTHING, blank=True, null=True)
    qiniu = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'BLOG'

    def __str__(self):
        return self.blog_name

class ArticleTop(models.Model):
    article_id = models.IntegerField(primary_key=True)
    is_top = models.IntegerField(blank=True, null=True)
    datetime_top = models.DateTimeField(blank=True, null=True)
    user_id = models.IntegerField(blank=False, null=False)

    class Meta:
        managed = False
        db_table = 'article_top'