import os
#激活虚拟环境
activate_this= os.path.join("###")
exec(open(activate_this).read(),dict(__file__=activate_this))

from waitress import serve
from xyz.wsgi import application

if __name__ == '__main__':
    serve(application, port='8000')