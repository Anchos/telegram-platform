from telegram.ext import CommandHandler, Updater
from telegram import Bot, Chat,TelegramError
import threading


class TelegramCustomBot:
    updater = Updater(token='459744558:AAEm1FxxzQ3KblbACDJjAWLQkDRnLK5TuFc')
    bot = updater.dispatcher.bot
    
    thread = None
    
    database = None
    
    def proveUser(self, bot, update):
        messageArgs = update.message.text.split(" ")
        if self.database.Sessions.check(session_id=messageArgs[1]) if len(messageArgs) == 2 else False:
            self.database.Users.add(telegram_id=update.message.chat_id)
            if self.database.Sessions.setUser(telegram_id=update.message.chat_id, session_id=messageArgs[1]):
                bot.send_message(chat_id=update.message.chat_id, text='Accepted!')
            else:
                bot.send_message(chat_id=update.message.chat_id, text='Something went wrong...!')
        else:
            bot.send_message(chat_id=update.message.chat_id, text='Error! Try again!')
            return None
    
    def botWorker(self):
        init_command_handler = CommandHandler('start', self.proveUser)
        self.updater.dispatcher.add_handler(init_command_handler)
        self.updater.start_polling(clean=True)
    
    def __init__(self, database):
        self.database = database
        self.thread = threading.Thread(target=self.botWorker)
        self.thread.start()
        #self.botWorker()


def check_group(bot,channe_name):
    try:
        check=Bot.getChat(bot,chat_id=channe_name)
        return True
    except (TelegramError):
        return False
        
def check_group_admin(bot, channel_name):
    try:
        admins = Bot.getChatAdministrators(bot, chat_id=channel_name)
        for admin in admins:
            adminId = admin.user.id
            adminsIds=[]
            adminsIds.append(adminId)
            return adminsIds
    except (TelegramError):
        return None