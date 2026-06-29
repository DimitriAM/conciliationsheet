from asgiref.wsgi import WsgiToAsgi
from app import app

application = WsgiToAsgi(app)
