#For now there are some problems with run this on my system
#I'll fix them after came back home

#pip install flask
#pip install flask-socketio
#pip install eventlet
import flask
from flask import Flask as fl
import flask_socketio as flask_sio
from flask_socketio import SocketIO as sio, emit

import random

#Some functions
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

#Main app's body
testApp = fl(__name__)
testApp_secretKey = randomSentence(50)
testApp.config["SECRET_KEY"] = testApp_secretKey
testSio = sio(testApp)

#^Testing junk
ark = {0:[]}
#$Testing junk


#Test pure flask
@testApp.route("/")
def index():
    return """<html><body><div style="background-color:red; min-width:500px; min-height:500px">Aloha brother!</div></body></html>"""

@testApp.route("/login")
def login():
    return """<html><body><div style="background-color:yellow; min-width:500px; min-height:500px">Brother, you cannot sign in how...</div></body></html>"""

@testApp.route("/user/<username>")
def profile(username):
    return """<html><body><div style="background-color:blue; min-width:500px; min-height:500px">Dear brother, for now you have a name! You're {username}</div></body></html>""".format(username=username)
    
#Test Flask SocketIO
@testSio.on("connect", namespace="/socket.io")
def test_connect(message):
    #^Testing junk
    print("connect")
    ark[0].append(message)
    #$Testing junk
    if message["data"].lower() == "connect":
        emit("response", {"data" : "Connected"})
    else:
        emit("response", {"data" : "Wrong request!"})
    
@testSio.on("info", namespace="/socket.io")
def info(message):
    #^Testing junk
    print("info")
    ark[0].append(message)
    #$Testing junk
    if message["data"] == "777":
        emit("response", {"info" : "thisIsTruthTheInfo!"})
    else:
        emit("response", {"error" : "Wrong password!"})
        
@testSio.on("message", namespace="/socket.io")
def send_message(message):
    #^Testing junk
    print("message")
    ark[0].append(message)
    #$Testing junk
    emit("response", message)
    
testSio.run(testApp, host="localhost", port=5000, debug=True)