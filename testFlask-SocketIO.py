#^#Authot's comment
#Here are some additional commented code for the future testing and researching
#
#$#

#^#Install details
#pip3 install flask
#pip3 install flask-socketio==2.8.3
#pip3 install --upgrade python-socketio
#pip3 install eventlet
#$#

#pip3 install raven[flask] # for logging flask

#^#^#Imports

#^#Flask
#flask
import flask
from flask import Flask as fl, request as flask_req
#flask-socketio
import flask_socketio as flask_sio
from flask_socketio import SocketIO as sio, emit
#$#
"""
#^#Logging
#raven
from raven.contrib.flask import Sentry as flask_sentry
from raven.handlers.logging import SentryHandler as flask_sentry_handler
from raven import setup_logging as flask_sentry_setup
#logging
import logging
#$#
"""
#^#Anothers
import random
#$#

#$#$#

#^#^#Some functions
def randomSentence(lenRangeStart=0, lenRangeEnd=0):
    absLenMax = 255
    if lenRangeStart == 0 and lenRangeEnd == 0:
        len = random.randint(0, absLenMax)
    elif lenRangeEnd == 0 and lenRangeStart > 0:
        len = lenRangeStart
    elif lenRangeEnd > lenRangeStart and lenRangeStart > 0:
        len = random.randint(lenRangeStart, lenRangeEnd)
    else:
        raise AttributeError("aRandomSentence: bad len range")
        
    sentenceCharactersAlphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = ""
    
    for i in range(len):
        result += random.choice(sentenceCharactersAlphabet)
        
    return result
#$#$#

#^#^#^#Main app's body

#^#Declare and init Flask
flApp = fl(__name__)
flApp_secretKey = randomSentence(50)
flApp.config["SECRET_KEY"] = flApp_secretKey
#$#

#^#Declare and init Flask-SocketIO
flSioApp = sio(flApp)
#$#

"""
#^#Logging
    #Raven Sentry
sentrySentry = flask_sentry(testApp, logging=True, level=logging.DEBUG) #logging.WARNING
sentryHandler = flask_sentry_handler(sentrySentry.client)
#if not flask_sentry_setup(sentryHandler):
#    raise "ERROR: Configuring raven sentry failed!"
    #Default Logging
logger = logging.getLogger(__name__)
if not sentryHandler.__class__ in map(type, logger.handlers):
    logger.addHandler(sentryHandler)
#$#
"""

#^#Recived data history
recivedDataHistory = {}
def addRecivedDataaToHistory(requestTitle, data):
    requestTitle = str(requestTitle)
    try:
        recivedDataHistory[requestTitle].append(data)
    except:
        recivedDataHistory[requestTitle] = []
        recivedDataHistory[requestTitle].append(data)
#$#

#^#Flask
@flApp.route("/")
def index():
    return """<html><body><div style="background-color:red; min-width:500px; min-height:500px">Aloha brother!</div></body></html>"""

@flApp.route("/login")
def login():
    return """<html><body><div style="background-color:yellow; min-width:500px; min-height:500px">Brother, you cannot sign in how...</div></body></html>"""

@flApp.route("/user/<username>")
def profile(username):
    return """<html><body><div style="background-color:blue; min-width:500px; min-height:500px">Dear brother, for now you have a name! You're {username}</div></body></html>""".format(username=username)

@flApp.route("/shutdown")
def shutdownTheFlaskApp():
    shutdownFlask = flask_req.environ.get("werkzeug.server.shutdown")
    if shutdownFlask != None:
        shutdownFlask()
        return "<p><b>ShutedDown</b></p>"
    else:
        return "<p><b>Cannot ShutDown</b></p>"
#$#

#^#Flask SocketIO

@flSioApp.on("connect", namespace="/socket.io")
def connect():
    print("connect")
    emit("connect_res", {"status" : "OK"})
    
@flSioApp.on("info", namespace="/socket.io")
def info(data=None):
    print("info [{0}]".format(data))
    if not data == None:
        addRecivedDataaToHistory("info", data)
        
    if type(data) == dict:
        #if data.get("password") == 777:
        if str(data.get("password")).strip() == "777":
            emit("info_res", {"status" : "OK", "info" : "thisIsTruthTheInfo!"})
        else:
            emit("info_res", {"status" : "ERROR", "errorCode" : 401, "errorText" : "Access denied!"})
    else:
        emit("info_res", {"status" : "ERROR", "errorCode" : 400, "errorText" : "Wrong data format!"})
        
@flSioApp.on("message", namespace="/socket.io")
def send_message(data=None):
    print("message [{0}]".format(data))
    if not data == None:
        addRecivedDataaToHistory("message", data)
        
    emit("message_res", {"status" : "OK", "data" : data})

#$#

#$#$#$#

# #Test raven(logging) for flask
# @testApp.errorhandler()
# def log_error(error):
#     print("[RAVEN] ERROR: {0}".format(error))

  
if __name__ == "__main__":
    flSioApp.run(flApp, host="localhost", port=5000, debug=False, use_reloader=False)
