#^#Author's comment
#$#

#^#Install details
#pip3 install flask
#pip3 install flask-socketio
#pip3 install eventlet
#
#pip3 install py-postgresql
#
#pip3 install python-telegram-bot
#$#

#^#^#Imports

#^#Flask
#flask
import flask
from flask import Flask as fl
#flask-socketio
import flask_socketio as flask_sio
from flask_socketio import SocketIO as sio, emit
#tgbot
from telegramBot import TelegramCustomBot
#postgresql
import postgresql
#$#

#^#Anothers
import json, uuid
import random, time
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

#^#^#^#^#Main app's body

#^#Declare and init Flask
flApp = fl(__name__)
flApp.config["SECRET_KEY"] = randomSentence(50)
#$#

#^#Declare and init Flask-SocketIO
flSioApp = sio(flApp)
#$#

#^#Flask : Routs
@flApp.route("/")
def index():
    return """<html><body><div style="background-color:red; min-width:500px; min-height:500px">Aloha brother!</div></body></html>"""

@flApp.route("/login")
def login():
    return """<html><body><div style="background-color:yellow; min-width:500px; min-height:500px">Brother, you cannot sign in how...</div></body></html>"""

@flApp.route("/user/<username>")
def profile(username):
    return """<html><body><div style="background-color:blue; min-width:500px; min-height:500px">Dear brother, for now you have a name! You're {username}</div></body></html>""".format(username=username)
#$#

#^#Flask SocketIO : Api Stream

@flSioApp.on("stream", namespace="/api")
def streamResolver(data):
    """EXMPL
    data = \
    {
        id: int,
        action: "INIT" | "AUTH" | "GET" | "SET",
        type: "", #1st
        secret_token: "", #0st
        operation: "", #"status" #"process" #2nd
        state: "" #3rd
    }
    
    rData = \
    {
        type: "", #1st
        status: "", #2nd #OK, ERR
        error: { #2ndnd
            code: "",
            text: ""
        }
        operation: "", //"status" //"process" #3rd
        state: "", #3rdnd
        data: "" #4th
    }
    """
        
    if type(data) == dict:
        if (data["type"] == "INIT") if data.get("type") else False:
            rData = Session.new()
            rData["type"] = data["type"]
        elif  Session.check(data["session_id"]) if data.get("session_id") else False:
            if data["type"] == "AUTH":
                rData = Auth.handler(data)
            elif data["type"] == "USER":
                rData = User.handler(data)
            elif data["type"] == "server" and False: #Dev
                rData = Server.handler(data)
            elif data["type"] == "services" and False: #Dev
                rData = Services.handler(data)
            elif data["type"] == "servers" and False: #Dev
                rData = Servers.handler(data)
            elif data["type"] == "users" and False: #Dev
                rData = Users.handler(data)
            else:
                rData = {"error":"bad_type"}
                #Wrong request type - Pshel v jepy
        else:
            rData = {"error":"bad_session"}
    else:
        rData = {"error":"bad_request_data_type"}
    
    if rData:
        if type(data) == dict:
            if data.get("type"):
                if not rData.get("type"):
                    rData["type"] = data["type"]
            
            if data.get("id"):
                rData["id"] = data["id"]
                
        emit("stream", rData)
#$#

#^#^#^#Main functions/classes

#^#^#Database

#^#Database set structure script
"""
CREATE TABLE "Users" (
	"id" serial NOT NULL,
	"telegram_id" integer NOT NULL UNIQUE,
	"user_info" json,
	CONSTRAINT Users_pk PRIMARY KEY ("id")
) WITH (
  OIDS=FALSE
);
CREATE TABLE "Sessions" (
	"session_id" uuid NOT NULL UNIQUE,
	"expiration" TIMESTAMP NOT NULL DEFAULT (now()+interval '2 days'),
	"user_id" integer,
	CONSTRAINT Sessions_pk PRIMARY KEY ("session_id")
) WITH (
  OIDS=FALSE
);
ALTER TABLE "Sessions" ADD CONSTRAINT "Sessions_fk0" FOREIGN KEY ("user_id") REFERENCES "Users"("id");
"""
#$#

#^#Database class
#One subclass per each database's table
#For start working, need get instance of Database class
#
#insert: f[1] - number of inserted
#select: f[][] - selecting result where first - row, second - column
class Database:
    dbConnectingCredentials = { \
    "login" : "devUser", \
    "password" : "1234567890Qq", \
    "address" : "127.0.0.1", \
    "port" : 5432, \
    "databaseName" : "telega" \
    }
    connectingAttempts = 3
    
    db = None
    
    def __init__(self, connectCredentials=None, **kwargs):
        if kwargs.get("login") and kwargs.get("password") and kwargs.get("databaseName"):
            connectCredentials = { \
            "login" : kwargs["login"], \
            "password" : kwargs["password"], \
            "address" : kwargs["address"] if kwargs.get("address") else "127.0.0.1", \
            "port" : kwargs["port"] if kwargs.get("port") else 5432, \
            "databaseName" : kwargs["databaseName"] \
            }
            self.dbConnectingCredentials = connectCredentials
        elif not connectCredentials:
            connectCredentials = self.dbConnectingCredentials
            
        for i in range(self.connectingAttempts, 0,-1):
            if i == 0:
                raise AttributeError("Database:__init__: Cannot connect to database with using followed credentials: {0}".fromat(self.dbConnectCredentials))
            
            try:
                self.db = postgresql.open('pq://{login}:{password}@{address}:{port}/{databaseName}'.format(login=connectCredentials["login"], password=connectCredentials["password"], address=connectCredentials["address"], port=connectCredentials["port"], databaseName=connectCredentials["databaseName"]))
            except Exception as error:
                print("Database:__init__: Error at connecting to database!\n{0}\nTry again... ".format(error))
                time.sleep(1.5)
                continue
            else:
                break
            
                
        self.Users = self.Users(self)
        self.Sessions = self.Sessions(self)
    
    def __call__(self, connectCredentials=None, *args, **kwargs):
        if connectCredentials:
            self.__init__(self, connectCredentials=connectCredentials)
        elif kwargs.get("login") and kwargs.get("password") and kwargs.get("databaseName"):
            connectCredentials = { \
            "login" : kwargs["login"], \
            "password" : kwargs["password"], \
            "address" : kwargs["address"] if kwargs.get("address") else "127.0.0.1", \
            "port" : kwargs["port"] if kwargs.get("port") else 5432, \
            "databaseName" : kwargs["databaseName"] \
            }
            self.__init__(self, connectCredentials=connectCredentials)
        else:
            self.__init__(self)
    
    def reconnect(self):
        self.__init__(self)
            
    def ifReconnect(self):
        if self.db.closed:
            self.reconnect(self)

    class Users:
        db = None
        
        def __init__(self, outself):
            self.db = outself.db
            #Add user
            self.addUser = self.db.prepare(r"""INSERT INTO "Users" ("id", "telegram_id") VALUES (DEFAULT, $1::integer)""")
            self.addUserFull = self.db.prepare(r"""INSERT INTO "Users" ("id", "telegram_id", "user_info") VALUES (DEFAULT, $1::integer, $2::json)""")
            #Check user
            self.checkUserById = self.db.prepare(r"""SELECT "id" FROM "Users" WHERE "id" = $1::integer""")
            self.checkUserByTelegramId = self.db.prepare(r"""SELECT "id" FROM "Users" WHERE "telegram_id" = $1::integer ORDER BY "id" ASC LIMIT 1""")
            self.checkUserBySessionId = self.db.prepare(r"""SELECT "user_id" FROM "Sessions" WHERE "user_id" IS NOT NULL AND "session_id" = $1::uuid ORDER BY "user_id" ASC LIMIT 1""")
            #Get user
            self.getUserById = self.db.prepare(r"""SELECT * FROM "Users" WHERE "id" = $1::integer""")
            self.getUserByTelegramId = self.db.prepare(r"""SELECT * FROM "Users" WHERE "telegram_id" = $1::integer ORDER BY "id" ASC LIMIT 1""")
            self.getUserBySessionId = self.db.prepare(r"""SELECT * FROM "Users" WHERE "id" = (SELECT "user_id" FROM "Sessions" WHERE "user_id" IS NOT NULL AND "session_id" = $1::uuid ORDER BY "user_id" ASC LIMIT 1)""")
            
        def check(self, **kwargs):
            try:
                if kwargs.get("session_id"):
                    if self.checkUserBySessionId(kwargs["session_id"]):
                        return True
                    else:
                        return False
                elif kwargs.get("telegram_id"):
                    if self.checkUserByTelegramId(kwargs["telegram_id"]):
                        return True
                    else:
                        return False
                else:
                    print("ERROR: Database:Users:check: Wrong arguments!")
                    return None #WRONG arguments
            except Exception as error:
                print("ERROR: Database:Users:check: Database operation failed! \n {0}".format(error))
                return None #DB operation failed
                
        def add(self, **kwargs):
            if kwargs.get("telegram_id"):
                try:
                    if kwargs.get("user_info"):
                        self.addUserFull(kwargs["telegram_id"], kwargs["user_info"])
                    else:
                        self.addUser(kwargs["telegram_id"])
                except Exception as error:
                    print("ERROR: Database:Users:add: Database operation failed! \n {0}".format(error))
                    return None #DB operation failed
                else:
                    return True
            else:
                print("ERROR: Database:Users:add: Wrong arguments!")
                return None #WRONG arguments
            
    class Sessions:
        db = None
        
        def __init__(self, outself):
            self.db = outself.db
            
            #Add session
            self.addSession = self.db.prepare(r"""INSERT INTO "Sessions" ("session_id", "expiration") VALUES ($1::uuid, DEFAULT)""")
            #Check session
            self.checkSessionBySessionId = self.db.prepare(r"""SELECT "session_id" FROM "Sessions" WHERE "session_id" = $1::uuid""")
            self.checkSessionByUserId = self.db.prepare(r"""SELECT "session_id" FROM "Sessions" WHERE "user_id" = $1::integer ORDER BY "user_id" ASC LIMIT 1""")
            self.checkSessionByTelegramId = self.db.prepare(r"""SELECT "session_id" FROM "Sessions" WHERE "user_id" = (SELECT "id" FROM "Users" WHERE "telegram_id" = $1::integer ORDER BY "id" ASC LIMIT 1) ORDER BY "user_id" ASC LIMIT 1""")
            #Get session
            self.getSessionBySessionId = self.db.prepare(r"""SELECT * FROM "Sessions" WHERE "session_id" = $1::uuid""")
            self.getSessionByUserId = self.db.prepare(r"""SELECT * FROM "Sessions" WHERE "user_id" = $1::integer ORDER BY "user_id" ASC LIMIT 1""")
            self.getSessionByTelegramId = self.db.prepare(r"""SELECT * FROM "Sessions" WHERE "user_id" = (SELECT "id" FROM "Users" WHERE "telegram_id" = $1::integer ORDER BY "id" ASC LIMIT 1) ORDER BY "user_id" ASC LIMIT 1""")
            self.getSessionsByUserId = self.db.prepare(r"""SELECT * FROM "Sessions" WHERE "user_id" = $1::integer ORDER BY "user_id" ASC""")
            self.getSessionsByTelegramId = self.db.prepare(r"""SELECT * FROM "Sessions" WHERE "user_id" = ((SELECT "id" FROM "Users" WHERE "telegram_id" = $1::integer ORDER BY "id" ASC)) ORDER BY "user_id" ASC""")
            #Set user
            self.setSessionUserIdBySessionId = self.db.prepare(r"""UPDATE "Sessions" SET "user_id" = $2::integer WHERE "session_id" = $1::uuid""")
            self.setSessionUserIdByTelegramIdBySessionId = self.db.prepare(r"""UPDATE "Sessions" SET "user_id" = (SELECT "id" FROM "Users" WHERE "telegram_id" = $2::integer ORDER BY "id" ASC LIMIT 1) WHERE "session_id" = $1::uuid""")
            #Extend expiration
            self.refreshSessionBySessionId = self.db.prepare(r"""UPDATE "Sessions" SET "expiration" = DEFAULT WHERE "session_id" = $1::uuid""")
            
        
        def check(self, **kwargs):
            try:
                if kwargs.get("session_id"):
                    if self.checkSessionBySessionId(kwargs["session_id"]):
                        return True
                    else:
                        return False
                #elif kwargs.get("user_id"):
                #    if self.checkSessionByUserId(kwargs["user_id"]):
                #        return True
                #    else:
                #        return False
                elif kwargs.get("telegram_id"):
                    if self.checkSessionByTelegramId(kwargs["telegram_id"]):
                        return True
                    else:
                        return False
                else:
                    print("ERROR: Database:Sessions:check: Wrong arguments!")
                    return None #WRONG arguments
            except Exception as error:
                print("ERROR: Database:Sessions:check: Database operation failed! \n {0}".format(error))
                return None #DB operation failed
                
        def new(self, **kwargs):
            if kwargs.get("session_id"):
                try:
                    self.addSession(kwargs["session_id"])
                except Exception as error:
                    print("ERROR: Database:Sessions:new: Database operation failed! \n {0}".format(error))
                    return None #DB operation failed
                else:
                    return True
            else:
                print("ERROR: Database:Sessions:new: Wrong arguments!")
                return None #WRONG arguments
                
        def setUser(self, **kwargs):
            if kwargs.get("session_id") and (kwargs.get("user_id") or kwargs.get("telegram_id")):
                try:
                    if kwargs.get("telegram_id"):
                        self.setSessionUserIdByTelegramIdBySessionId(kwargs["session_id"], kwargs["telegram_id"])
                    elif kwargs.get("user_id"):
                        self.setSessionUserIdBySessionId(kwargs["session_id"], kwargs["user_id"])
                except Exception as error:
                    print("ERROR: Database:Sessions:setUser: Database operation failed! \n {0}".format(error))
                    return None #DB operation failed
                else:
                    return True
            else:
                print("ERROR: Database:Sessions:setUser: Wrong arguments!")
                return None #WRONG arguments
                
        def getUser(self, **kwargs):
            try:
                if kwargs.get("session_id"):
                    session = self.getSessionBySessionId(kwargs["session_id"])[0]
                    if session:
                        return session[2]
                    else:
                        return False
                else:
                    print("ERROR: Database:Sessions:check: Wrong arguments!")
                    return None #WRONG arguments
            except Exception as error:
                print("ERROR: Database:Sessions:getUser: Database operation failed! \n {0}".format(error))
                return None #DB operation failed
            
        def refreshTime(self, **kwargs):
            if kwargs.get("session_id"):
                try:
                    self.refreshSessionBySessionId(kwargs["session_id"])
                except Exception as error:
                    print("ERROR: Database:Sessions:refreshTime: Database operation failed! \n {0}".format(error))
                    return None #DB operation failed
                else:
                    return True
            else:
                print("ERROR: Database:Sessions:refreshTime: Wrong arguments!")
                return None #WRONG arguments
        
DB = Database()
#$#

#$#$#
n3 = None
#^#^#Api handlers
class Session:
    def check(data):
        global n3
        n3 = data
        print(data)
        print(type(data))
        if data.get("session_id"):
            return DB.Sessions.check(data["session_id"])
            
    def new():
        sessionId = str(uuid.uuid4())
        if DB.Sessions.new(session_id=sessionId):
            return {"data":sessionId}
        else:
            return {"error":"internal_server_error"}
        
class Auth:
    def handler(data):
        if DB.Sessions.check(data["session_id"]) if data["session_id"] else False:
            return {"type":"AUTH", "error":"already_authorized"}
        else:
            return {"type":"AUTH", "action":"PROCESS"}
            
class User:
    def handler(data):
        if DB.Sessions.check(data["session_id"]) if data["session_id"] else False:
            telegramId = DB.Sessions.getUser(session_id=data["session_id"])
            if telegramId:
                print("Yeah! His tg-id: {0}".format(telegramId))
                return True
            else:
                print("You aren't logged in!")
                return False
        else:
            return False
class Server:
    def handler(data):
        pass
class Services:
    def handler(data):
        pass
class Servers:
    def handler(data):
        pass
class Users:
    def handler(data):
        pass
#$#$#
TCB = TelegramCustomBot(DB)
#$#$#$#$#


  
if __name__ == "__main__":
    flSioApp.run(flApp, host="localhost", port=5000, debug=False, use_reloader=False)
