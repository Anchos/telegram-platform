from telegram.ext import CommandHandler, Updater
from telegram import Bot, Chat, TelegramError
import asyncio
import websockets

loop = asyncio.get_event_loop()
updater = Updater(token='BOT_APT')
bot = updater.dispatcher.bot
async def send_id_token(cht_id):
    async with websockets.connect('ws://127.0.0.1:5678') as websocket:
        await websocket.send(cht_id)
        answ = await websocket.recv()
        print(" {}".format(answ))
def startCommand(bot, update):
    cht_id = str(update.effective_message.chat.id)
    token = str(update.effective_message.text).split(" ")
    if len(token)==2:
        token = str(update.effective_message.text).split(" ")
        cht_id=cht_id+' '+token[1]
        loop.run_until_complete(send_id_token(cht_id=cht_id))
        loop.close()
    else:
        bot.send_message(chat_id=update.message.chat_id,text="Where's token?")
def check_group(bot, channe_name):
    try:
        check = Bot.getChat(bot, chat_id=channe_name)
        return check
    except (TelegramError):
        pass


def check_group_admin(bot, channel_name):
    try:
        adm = Bot.getChatAdministrators(bot, chat_id=channel_name)
        for key in adm:
            s = key.user.id
            str = []
            str.append(s)
            return str
    except (TelegramError):
        pass


def start_bot():

    start_command_handler = CommandHandler('start', startCommand)
    updater.dispatcher.add_handler(start_command_handler)
    updater.start_polling(clean=True)


start_bot()
