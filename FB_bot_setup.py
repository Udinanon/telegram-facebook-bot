#! python3.6
# FB_Bot_setup.py - Setup for FB_Bot and for FB_Bot_adder
# version is 20181001
# if you want to say anything go to @Udinanon on Telegram or check my email here on GitHub
# DISTRIBUTED UNDER GNU LGPL v3 or latest
# THE AUTHOR OF THE SCRIPT DOES NOT AUTHORIZE MILITARY USE OF HIS WORK OR USAGE IN ANY MILITARY-REALTED ENVIROMENT WITHOUT HIS EXPLICIT CONSENT

# TO DO LIST:
    # better comment the code //getting better
    # reorder the code and make it more readable //it's getting better
    # handle HD photos
    # handle continue reading in very long posts

import configparser
from requests_html import HTMLSession
import csv
import os

TG_BASE = "https://api.telegram.org/bot{}/"
ini_files=["./FB_Bot.ini", "./FB_adder.ini"]
log_settings={"debug_level":"INFO", "date_structure":"%y%m%d", "log_file_name":"./FB_"}

def get_mobile_URL(URL):
    return URL[:8:] + "m" + URL[11::]

def get_page_name(URL):
    session=HTMLSession()
    URL=get_mobile_URL(URL)
    r=session.get(URL)
    name=r.html.find("title", first =True)
    return name.text.strip(" - Post | Facebook")

def advanced_config():
    input("""There should be something here to configure the logging but I'm tired and this bot is waaay too complex to be such badly designed
If you actually are an advanced user you can come help me on github https://github.com/MorenK1/telegram-facebook-bot or you can conjtact me via telegram @udinanon and tell me why you like it so much
Press any key to go back to the rest of the setup""")

def main():
    input("""Your FB Bot will now be set in the cuirrent folder, you will need:
    A list of the facebook pages you want to see
    A Telegram bot admin of the channels where you want to see the FB posts
    The bot's TOKEN (if you don't know what this is see https://kutt.it/fhVkGx)
    A few minutes
If you want to keep the default settings just press Enter
Ready?
    """)
    FB_Bot_ini=configparser.ConfigParser()
    FB_Bot_ini.add_section("BASIC")
    FB_Bot_ini.add_section("LOG")
    ans=input("""Are you an advanced user who wants to customize logging?
Default is No
(y/n)
    """)
    if ans.lower().startswith("y"):
        log_settings=advanced_config()
    FB_Bot_ini["LOG"]=log_settings
    ans=input("""Paste your bot's Telegram token
There are no defaults here, you can skip this and paste it later in the .ini file
This input will not be checked
    """)
    FB_Bot_ini["BASIC"]["bot_token"]=str(ans)
    input("""Now we will start building the pages.csv file that the Bot will use as a guide
When done with a channel, enter 'DONE'
""")
    data={}
    while True:
        channel=input("""Paste here a @channelname you want to use the bot on
Be sure that the bot has admin priviledges there
""")
        if channel=="DONE":
            break
        data[channel]=[]
        while True:
            page=input("Now paste the link to the posts section of a FB page you want on that channel\n")
            if page=="DONE":
                break
            page_name=get_page_name(page)
            print("Ok with page ", page_name)
            data[channel].append(page)
    ans=input("""paste now, if you want, a custom name for your .csv file
The default is FB_pages.csv
""")
    if ans!="":
        csv_file=ans
    else:
        csv_file="./FB_pages.csv"
    FB_Bot_ini["BASIC"]["pages_file"]=csv_file
    lines=[]
    for channel, pages in data.items():
        for page in pages:
            page_name=get_page_name(page)
            human_name=page_name+" @ "+channel
            line=[str(human_name), str(page_name), str(page.strip()), "0", str(channel)]
            lines.append(line)
    with open(csv_file, "w+", newline='', encoding='utf_8') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow(("HUMAN REDABLE", "NAME", "URL", "LAST_TIME", "TOKEN", "ID"))
        for row in lines:
            writer.writerow(row)
    ans=input("""How often you want the bot to wake up and check for new content?
This might slightly impact resources and bandwidth, expecially on low end machines
Default is 30 mins
""")
    if ans!="":
        FB_Bot_ini["BASIC"]["interval_between_updates"]=str(60*ans)
    else:
        FB_Bot_ini["BASIC"]["interval_between_updates"]="1800"
    ans=input("""Do you want to let people add pages to your bot via Telegram?
You will have to approve all the entries manually
If no, the adder portion of the bot will be deleted
Default is Yes
(y/n)
""")
    if ans.lower().startswith("n"):
        os.remove("./FB_page_adder_bot.py")
        ini_files=["FB_Bot.ini"]
    else:
        FB_Bot_ini.add_section("ADDER")
        ans=input("""Paste now custom file to log all approved page additions
Default is ./New_FB_pages.log
""")
        if ans!="":
            FB_Bot_ini["ADDER"]["new_pages_file"]=ans
        else:
            FB_Bot_ini["ADDER"]["new_pages_file"]="./New_FB_pages.log"
        FB_adder_ini=configparser.ConfigParser()
        FB_adder_ini.add_section("BASIC")
        FB_adder_ini.add_section("LOG")
        FB_adder_ini["BASIC"]["output_file"]=FB_Bot_ini["ADDER"]["new_pages_file"]
        FB_adder_ini["BASIC"]["bot_token"]=FB_Bot_ini["BASIC"]["bot_token"]
        FB_adder_ini["BASIC"]["FB_pages_file"]=FB_Bot_ini["BASIC"]["pages_file"]
        FB_adder_ini["BASIC"]["temp_file"]="./Temp_new_pages_requests.txt"
        FB_adder_ini["LOG"]=log_settings
        FB_adder_ini["LOG"]["log_file_name"]=FB_adder_ini["LOG"]["log_file_name"]+"adder_"
        FB_Bot_ini["ADDER"]["last_request_unix"]="0"
        ans=input("""If you know your Telegram ID (not the @username, the actual numerical ID) paste it now
It will be used to confirm requests sent to the bot
If you don't know your ID enter 'NULL'
Like for tokens there is no default, if left empty it will be empty
""")
        if ans.upper().strip().strip("'")=="NULL":
            msg_text=input("""Now we will find out your Telegram ID
Send a direcdft text message to the bot now and paste the same text here
""")
            r=requests.get(TG_BASE.format(FB_Bot_ini["BASIC"]["bot_token"])+"getUpdates")
            if r.status_code!=200:
                print("The bot is unreachable from this computer, try again after cheking the token and the connection.\n I will crash now")
                time.sleep(5)
                raise BaseException
            else:
                for update in json.loads(r.content):
                    if update["message"]["text"]==msg_text:
                        ans=input("Is your username: "+str(update["message"]["from"]["username"]+"\n(y/n)"))
                        if ans.lower().startswith("y"):
                            user_id=update["message"]["from"]["id"]
                            break
                    print("There might have been an error in parsing the bot's updates, this has caused a critical faliure.\nI will now crash")
                    time.sleep(5)
                    raise BaseException
                FB_adder_ini["BASIC"]["admin_id"]=str(user_id)
        ans=input("""Enter now the maximum number of pages to be added for a single user request
The default is 10
""")
        if ans!="":
            FB_adder_ini["BASIC"]["max_n_of_pages_per_request"]=str(int(ans))
        else:
            FB_adder_ini["BASIC"]["max_n_of_pages_per_request"]="10"
    with open("./FB_Bot.ini", "w+", encoding="utf-8") as file:
        FB_Bot_ini.write(file)
    with open("./FB_adder.ini", "w+", encoding="utf-8") as file:
        FB_adder_ini.write(file)
    input("The setup is complete, it should work now.\n Press any key to close")


main()
