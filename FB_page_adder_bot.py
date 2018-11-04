#! python3
# FB_page_adder_bot.py - script to interface via Telegram in support to FB_Bot.py, used to add new pages and channel to the running list
# to avoid race conditions or other errors, this writes to an intermediate CSV file that is then read by FB_bot.py, and it handles adding the pages
# version is 20180908
# if you want to say anything go to @Udinanon on Telegram or check my email here on GitHub
# DISTRIBUTED UNDER GNU LGPL v3 or latest
# THE AUTHOR OF THE SCRIPT DOES NOT AUTHORIZE MILITARY USE OF HIS WORK OR USAGE IN ANY MILITARY-REALTED ENVIROMENT WITHOUT HIS EXPLICIT CONSENT

# is this thing vulnerable to code injection?


import requests
import logging
import time
import re
import argparse
import configparser
import csv
import telegram
from telegram.ext import Updater, CommandHandler, Filters, CallbackQueryHandler, ConversationHandler, MessageHandler
from telegram import Bot

CHANNEL, PAGES, SELECT_SINGLE_CHANNEL=range(3)
FB_Page_regex = re.compile(r"https:\/\/www\.facebook\.com")
TIME_regex = re.compile(r"(#)(1[0-9]{9})(#)")

def argument_parser():  # description of the program and command line arguments
    parser = argparse.ArgumentParser(description="Support script to add new FB pages and channels to running list")
    parser.add_argument("-ini_file", dest="ini_file", default="./FB_adder.ini", help="Path to INI file that sources all basic info to the bot, see the GitHub for more; defaults to ./FB_adder.ini")
    return vars(parser.parse_args())

def config_parser(ini_file):
    config=configparser.ConfigParser(interpolation=None)
    config.read(ini_file)
    basic_config, log_config=config["BASIC"], config["LOG"]
    numeric_level=getattr(logging, log_config["debug_level"].upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level in configuration file: " + log_config["debug_level"])
    log_config["log_file"]=log_config["log_file_name"]+get_day(log_config["date_structure"])+".log"
    logging.basicConfig(filename = log_config["log_file"], level = numeric_level)
    global out_file
    out_file=basic_config["output_file"]
    global pages_file
    pages_file=basic_config["FB_pages_file"]
    global admin_id
    admin_id=basic_config["admin_id"]
    global temp_pages
    temp_pages=basic_config["temp_file"]
    global TOKEN
    TOKEN=basic_config["bot_token"]
    global max_n_of_pages
    max_n_of_pages=int(basic_config["max_n_of_pages_per_request"])
    return basic_config, log_config

def update_logfile_date(log_config):
    numeric_level = getattr(logging, log_config["debug_level"].upper(), None)
    log_config["log_file"]=log_config["log_file_name"]+get_day(log_config["date_structure"])+".log"
    logging.basicConfig(filename = log_config["log_file"], level = numeric_level)


# BOT HANDLERS

def start(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="""Benvenuto!
    Questo bot permette di seguiire le tue pagone Facebook preferite direttamente da Telegram!
    Per veder le pagine attualmente attive ed i loro canali Telegram usa il comando /see_all, se invece vuoi aggiungere una pagina o un canale puoi usare il comando /add.
    Tutte le richieste sono confermate manualmente e la funzione è ancora in beta, in caso di errore inaspettato contatta lo Sviluppatore @udinanon
    Se sei interessato a come funziona il Bot, se vuoi modificarlo o attivare una tua versione vieni su [GitHub](https://github.com/MorenK1/telegram-facebook-bot)""", parse_mode=telegram.ParseMode.MARKDOWN)

def error(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Your message was not recognized, please try again")


def add(bot, update, user_data):
    bot.sendMessage(chat_id=update.message.chat_id,
                    text="Ok so to add a page we first need a public channel, then you need to add this bot as an admin to said channel.\nAfterwards, send me the @CHANNEL_LINK with command /channel\n Es: /channel @ItalianGoodposting")
    user_data["USER_NAME"] = str(update.message.from_user.username)
    print(user_data["USER_NAME"]+" is trying to add a channel!")
    return CHANNEL

def channel(bot, update, args, user_data):
    print("CHANNEL")
    if len(args) != 1:
        bot.sendMessage(chat_id=update.message.chat_id, text="There was an error reading the name of the channel, they aren't supposed to have spaces\nThis is what the bot is reading: '" +
                        str(args) + "'\nIf you followed our instructions correctly, you might want to contact the Developer")
    try:
        channel_message=bot.sendMessage(chat_id=str(args[0]), text="TEST FOR THE CHANNEL")
        time.sleep(5)
        bot.deleteMessage(chat_id=str(args[0]), message_id=channel_message["message_id"])
        user_data["CHANNEL_ID"] = str(args[0])
        user_data["CHANNEL_NAME"] = str(channel_message["chat"]["title"])
        bot.sendMessage(chat_id=update.message.chat_id, text="Ok the channel " + str(args[0]) +
                        " seems to be working correctly, now send me the links to the posts sections of the Facebook pages you are interested in, one per line, with no spaces or anything\nMaximum numer of pages is " + str(max_n_of_pages) + ", exceeding pages will be ignored")
        return PAGES
    except Exception as e:
        bot.sendMessage(chat_id=update.message.chat_id, text="There was an error trying to write on the channel, here's some detail:\n" +
                        str(e) + "\nIf you followed our instructions correctly, you might want to contact the Developer")
        logging.error("There was an error trying to write on the channel, here's some detail:\n" + str(e))


def pages(bot, update, user_data):
    pages = update.message.text.splitlines()
    pages = list(filter(lambda x: bool(re.search(r"https:\/\/www\.facebook\.com", x)), pages))
    user_data["PAGES"] = []
    global max_n_of_pages
    if len(pages) > max_n_of_pages:
        n_skipped_pages = len(pages) - max_n_of_pages
        bot.sendMessage(chat_id = update.message.chat_id, text = "You submitted more than "+str(max_n_of_pages)+" pages, the leading " + \
                        str(n_skipped_pages) + " pages were skipped")
        pages=pages[:max_n_of_pages]
    for page in pages:
        try:
            r=requests.get(page)
            user_data["PAGES"].append(page)
        except Exception as e:
            bot.sendMessage(chat_id = update.message.chat_id,
                            text = "There was a problem with one of the pages, it might be offline or not formatted correctly\nException: " + str(e) + " for page " + str(page)+"\nIn case it's not contact the Developer")
    bot.sendMessage(chat_id = update.message.chat_id, text = "The pages were read correctly, here is what the bot found:\n" + " ".join(pages))
    # if len(pages)==1:
    #     buttons=InlineKeyboardMarkup([InlineKeyboardButton("Yes", callback_data="yes"), InlineKeyboardButton("No", callback_data="no")])
    #     bot.sendMessage(chat_id=update.message.chat_id, text="Your channel only has one page, if you want we could hide the page's name to avoid repetition with the Channel name", reply_markup=buttons)
    #     return SELECT_SINGLE_CHANNEL
    # else:
    bot.sendMessage(chat_id = update.message.chat_id,
                    text = "The setup process has been completed, your channel should start being active in a couple of hours, if nothing happens contact the Developer")
    user_data["USER_ID"]=update.message.from_user.id
    time=save_data(user_data)
    ask_admin(bot, user_data, time)
    return ConversationHandler.END


def accept(bot, update):
    print("ACCEPT FROM "+str(update.message.from_user))
    if str(update.message.from_user.id)==str(admin_id):
        msg=update.message.reply_to_message.text
        accept_time=msg[:10:]
        data, request=find_time(accept_time)
        with open(temp_pages, "w") as file:
            file.writelines(data)
        with open(out_file, "a") as file:
            print("ADDING: "+str(request))
            file.writelines(request)
            req_time=str(int(time.time()))
            print(req_time)
            file.write("#"+req_time+"#\n")

def deny(bot, update):
    if str(update.message.from_user.id)==str(admin_id):
        msg=update.message.reply_to_message.message.text
        time=msg[:10:]
        data, request=find_time(time)
        with open(temp_pages, "w") as file:
            file.writelines(data)

def see_all(bot, update):
    global pages_file
    try:
        with open(pages_file, "r", encoding = 'utf_8') as file:
            next(file, None)
            reader=csv.reader(file)
            pages=list(reader)
        logging.debug("ALL PAGES: " + str(pages))
        message="Here are all the pages and channels currently handled\nStructure is: Human Readable data, page URL, channel\n"
        for page in pages:
            message=message + str(page[0]) + " " + str(page[2]) + " " + str(page[4]) + "\n"
            bot.sendMessage(chat_id = update.message.chat_id, text = message)
    except IOError:
        logging.warning("Nessun file di input è stato trovato a " + pages_file)

def see(bot, update, args):
    args=" ".join(args.lower())
    global pages_file
    try:
        with open(pages_file, "r", encoding = 'utf_8') as file:
            next(file, None)
            reader=csv.reader(file)
        pages=list(reader)
        logging.debug("ALL PAGES: " + str(pages))
        message="Here are all the pages with the requested name currently handled\nStructure is: Human Readable data, page URL, channel ID\n"
        count=0
        for page in pages:
            if args in page[0].lower():
                count += 1
                message=message + str(page[0]) + " " + str(page[2]) + " " + str(page[5]) + "\n"
        if count == 0:
            bot.sendMessage(chat_id = update.messages.chat_id, text = "No pages with that name were found in the list")
        else:
            bot.sendMessage(chat_id = update.messages.chat_id, text = message)
    except IOError:
        logging.warning("Nessun file di input è stato trovato a " + pages_file)


# FUNCTIONS USED

def get_day(form="%y%m%d"):
    day = time.strftime(str(form))
    return day

def find_time(time):
    with open(temp_pages, "r") as file:
        data=file.readlines()
    j=0
    print("LOOKING FOR "+str(time))
    for i in range(len(data)):
        if TIME_regex.search(data[i]):
            if int(data[i].strip().strip("#")) == int(time):
                request=data[j:i:]
                data=data[:j:]+data[i+1::]
                print("FOUND IT!")
                return data, request
            else:
                j=i
    print("MA CHE CAZZ")

def ask_admin(bot, user_data, request_time):
    pages="\n".join(user_data["PAGES"])
    bot.sendMessage(chat_id=admin_id, text=str(request_time)+"\n"+str(user_data["USER_NAME"])+"\n"+str(user_data["USER_ID"])+"\n"+str(user_data["CHANNEL_ID"]) + "\n" + str(user_data["CHANNEL_NAME"])+"\n"+pages)

def save_data(user_data):
    with open(temp_pages, "a") as file:
        file.write(str(user_data["USER_NAME"])+"\n"+str(user_data["USER_ID"])+"\n")
        file.write(str(user_data["CHANNEL_NAME"]) + "\n" + str(user_data["CHANNEL_ID"])+"\n")
        for page in user_data["PAGES"]:
            file.write(str(page)+"\n")
        request_time=int(time.time())
        file.write("#" + str(request_time) + "#\n")
    return request_time



def main():
    args=argument_parser()
    basic_config, log_config=config_parser(args["ini_file"])
    print("FB ADDER BOT")
    global outfile
    logging.info("OUTPUT FILE: " +out_file)
    updater=Updater(token =TOKEN)
    bot=Bot(token =TOKEN)
    dispatcher=updater.dispatcher
    start_handler=CommandHandler("start", start)
    con_handler=ConversationHandler(entry_points = [CommandHandler("add", add, pass_user_data=True)],
        states = {CHANNEL: [CommandHandler("channel", channel, pass_args=True, pass_user_data=True)], PAGES:[MessageHandler(Filters.text, pages, pass_user_data=True)]},
        fallbacks=[MessageHandler(Filters.all, error)], conversation_timeout=0)
    see_handler=CommandHandler("see", see)
    see_all_handler=CommandHandler("see_all", see_all)
    accept_handler=CommandHandler("accept", accept)
    deny_handler=CommandHandler("deny", deny)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(see_all_handler)
    dispatcher.add_handler(see_handler)
    dispatcher.add_handler(accept_handler)
    dispatcher.add_handler(deny_handler)
    dispatcher.add_handler(con_handler)
    updater.start_polling()
    while True:
        time.sleep(10000)
        update_logfile_date(log_config)
if __name__ == "__main__":
    main()
