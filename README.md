# telegram-facebook-bot
A poorly coded spider for Facebook pages in Python 3.6. Loads content from FB, formats it and sends it to Telegram channels
It's incomplete: supports text, link, videos, photos, gifs and shares, not other kinds of content and can be buggy

# How to use
The basic functionality is provided by FB_Bot.py: it will do the scraping and will send the data collected to the Telegram channels;
It reads from a .csv file for a list of the Fb pages, the Telegram channel to which it will send the data, the name it should display on top of the posts and other stuff. For more info see below.
It also loads a .ini file for other things like the Telegram bot Token, how often to update, where is the .csv file, general log settings and other things, again for more info see below
The FB_page_adder_bot.py makes it possible to add FB pages via Telegram itself. It also loads data from a different .ini file and can do a few more things like the command /see_all that lets user see all the pages being served by the bot, reading the .csv file. All the requests will have to be approved by an admin via Telegram, they will be routed to them and they will accept or denyed them with /accept or /deny. This script is not needed
Lastly the FB_setup.py is a script that generates basic .ini files and basic .csv files, making it really to setup a new instance of the bot

# .csv File
	"HUMAN REDABLE","NAME","URL","LAST_TIME","ID"
This is the firts line of the csv file and is how the data is structured:
[a human readable name for the page, not used by the bot], [name of the page to display on Telegram posts], [URL of the FB page post section], [unix time of the last post that the bot has processed for this page], [ID of Telegram channel where to route the posts]
The first line is not read by the bot and is kept this way as a reference for manual editing of the file, the rest of the lines will be used.
Improperly structured data will most likely crash the bot. All entries are to be put in quotation marks.

# .ini File
	[BASIC]
	pages_file = ./FB_pages.csv
	interval_between_updates = 900
	bot_token = [YOUR BOT TOKEN]

	[ADDER]
	new_pages_file = ./New_FB_pages.log
	last_request_unix = 

	[LOG]
	debug_level = INFO
	log_file_name = ./FB_
	date_structure = %y%m%d
	log_file = [CURRENT LOG FILE NAME]

This is the basic structure of the FB_Bot.ini file, similar to the FB_adder.ini 

	[BASIC]
	#the first three are all local paths to your files, the default ones should be ok
	output_file=./New_FB_pages.log
	FB_pages_file=./FB_pages.csv
	temp_file=./Temp_new_pages_requests.txt
	admin_id=[ADMIN TELEGRAM ID]
	bot_token=[YOUR BOT TOKEN]
	max_n_of_pages_per_request=10

	[LOG]
	#valid levels are DEBUG, INFO, WARNING, CRITICAL; see logging module for python 
	debug_level=INFO
	#logfiles also have the date and the format at their filename's end, such as [log_file_name]_YYMMDD.log
	#change the date_structure according to time.strftime() of python
	#default is ./FB_adder_YYMMDD.log
	log_file_name=./FB_adder_
	date_structure=%y%m%d

The name of the .ini files can be changed as a command line argument for the scripts; the interval is in seconds.
I don't really know what else to put here, if you have any problems, errors, doubts etc write me an email
