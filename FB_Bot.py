#! python3
# FB_Bot.py - Scraper for Facebook pages that sends posts to Telegram channels
# version is 20180316
# if you want to say anything go to @Udinanon on Telegram or check my email here on GitHub
# DISTRIBUTED UNDER GNU LGPL v3 or latest
# THE AUTHOR OF THE SCRIPT DOES NOT AUTHORIZE MILITARY USE OF HIS WORK OR USAGE IN ANY MILITARY-REALTED ENVIROMENT WITHOUT HIS EXPLICIT CONSENT

# TO DO LIST:
	# better comment the code //getting better
	# reorder the code and make it more readable //it's getting better
	# add command line arguments //partial
	# handle HD photos
	# handle gifs //PARTIALLY
	# handle shares
	# handle continue reading in very long posts
	#will probaby start using the Facebook API as soon as I understand how to use it for this
	#might want to look at what can be simplified or implemented using the select function of BeautifulSoup

from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote
import csv
import requests
import time
import cgi
import re
import logging
import argparse

TG_BASE = "https://api.telegram.org/bot{}/"
# This is used to check the length of messages later
TAG_RE = re.compile(r'<[^>]+>')
USERAGENT={"User-Agent":'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'}


# basic stuff
def get_url(url):  # get webpages as general files
	response = requests.get(url, headers=USERAGENT)
	logging.debug("GET URL:" + url + "\nRESPONSE:" + response.reason)
	return response.content


def get_date():
	date = time.strftime("%Y-%m-%d+%H.%M")
	return date


def get_day():
	day = time.strftime("%y%m%d")
	return day

# id is used to determine the age of a post and to avoid duplicates

'''
The CSV file is just a list of the FB pages to be scarped, the first line is ignor4ed as it is supposed to be human readable
It is structured as follows:
	[0] A human readable name, not used by the script
	[1] The name that is sent as the title of the post, usually a null string for single page channels and the page's name for multipage channels
	[2] The URL of the posts section of the page
	[3] The UNIX time of the last read post, set to 0 if its the first time so every post is sent
	[4] Telegram Token of the bot that will carry out the operations
	[5] Telegram channel ID on which the posts are suposed to go
'''
def update_csv(pages, input_file): #write new data to csv of Facebook Pages
	with open(input_file, "w", newline='', encoding='utf_8') as file:
		writer = csv.writer(file, quoting=csv.QUOTE_ALL)
		writer.writerow(("HUMAN REDABLE", "NAME", "URL", "LAST_TIME", "TOKEN", "ID"))
		for row in pages:
			writer.writerow(row)


def get_post_time(post): #find the UNIX time of the post
	time_area = post.select_one("abbr._5ptz")
	post_time = time_area["data-utime"]
	return int(post_time)


def add_video_link(post): #add video link to top of the post's text
	text = "<a href='" + post["video"] + "'>VIDEO</a> \n" + post["text"]
	return text


def add_link(post): #add link to the top of the post's text
	text = "<a href='" + post["link"] + "'>LINK</a> \n" + post["text"]
	return text


def add_link2post(post): #add link to the Facebook post at the bottom of the post
	post["link2post"] = handle_link2post(post)
	text = str(post["text"]) + "\n<a href='" + str(post["link2post"]) + "'>POST</a>"
	return text


def add_page_name(post): #add page name in bold to the top of the post
	text = "<b>" + str(post["page_name"]) + "</b>\n" + post["text"]
	return text


def remove_tags(text): #used to check if the shown message will be <200 chars in Telegram
	return TAG_RE.sub('', text)


def argument_parser():  # description of the program and command line arguments
	parser = argparse.ArgumentParser(
	    description="Scraper for Facebook pages that sends posts to telegram channels, does not support gifs or videos as of now")
	parser.add_argument("-pages_file", dest="input_file", default="./FB_pages.csv",
	                    help="CSV file from which Facebook pages will be loaded, defaults to ./FB_pages.csv")
	parser.add_argument("-log_file", dest="log_file", default="./FB_" +
	                    get_day() + ".log", help="Path to log file, defaults to ./FB_YYMMDD.log")
	parser.add_argument("-debug_LVL", dest="debug_LVL",
	                    default="DEBUG", help="Logging level, defaults to DEBUG")
	return vars(parser.parse_args())


# telegram relaying

def send_post(post): #for text posts
	URL = TG_BASE.format(str(post["BOT"])) + "sendMessage"
	data = {"chat_id": post["channel_ID"], "text": post["text"],
	    "parse_mode": "html", "disable_web_page_preview": post.get("no_link")}
	r = requests.get(URL, params=data, headers=USERAGENT)
	logging.info("SENDING POST, RESPONSE:" + r.reason +
	             " STATUS CODE:" + str(r.status_code))
	if r.status_code != 200:
		logging.critical("THERE WAS AN ERROR IN A REQUEST IN send_post")
		logging.critical("URL: " + str(r.url))
		logging.critical("DATA: " + str(data))
		logging.critical("REASON: " + str(r.reason))
		logging.critical("RESPONSE: " + str(r))
	return r.json()["result"]["message_id"]


def send_photo_multipart(post): #download and upload photos, used as backup when sending the URL doesn't work
	with open("temp.png", "wb") as file:
		file.write(requests.get(post["photo"]).content)
	photo = {"photo": open("temp.png", "rb")}
	URL = TG_BASE.format(str(post["BOT"])) + "sendPhoto"
	data = {"chat_id": post["channel_ID"], "caption": post["text"],
	    "parse_mode": "html", "reply_to_message_id": post.get("reply_id")}
	r = requests.post(URL, data=data, files=photo, headers=USERAGENT)
	if r.status_code != 200:
		logging.critical("THERE WAS A N ERROR IN A REQUEST IN send_photo_multipart")
		logging.critical("URL: " + str(r.url))
		logging.critical("DATA: " + str(data))
		logging.critical("REASON: " + str(r.reason))
		logging.critical("RESPONSE: " + str(r))
	return r


def send_photo(post): #send photo via URL, with the text if <200
	if len(remove_tags(post["text"])) > 195: #if the text is too long it isn't shown correctly by Telegram
		post["reply_id"] = send_post(post) #so it's sent first and then the photo as a reply to it
		post["text"] = ""
	URL = TG_BASE.format(str(post["BOT"])) + "sendPhoto"
	data = {"chat_id": post["channel_ID"], "photo": post["photo"], "caption": post["text"],
	    "parse_mode": "html", "reply_to_message_id": post.get("reply_id")}
	r = requests.get(URL, params=data, headers=USERAGENT)
	logging.info("SENDING PHOTO, RESPONSE:" + r.reason +
	             " STATUS CODE:" + str(r.status_code))
	if (r.status_code == 400 and r.json()["description"] == "Bad Request: wrong file identifier/HTTP URL specified"): #when Facebook links don't work
		logging.warning("URL: " + str(r.url))
		logging.warning("THERE WAS A PROBLEM IN THE REQUEST, TRYING TO MULTIPART IT")
		logging.warning("DATA: " + str(data))
		r=send_photo_multipart(post)
	if r.status_code != 200:
		logging.critical("THERE WAS AN ERROR IN A REQUEST IN send_photo")
		logging.critical("URL: " + str(r.url))
		logging.critical("DATA: " + str(data))
		logging.critical("REASON: " + str(r.reason))
		logging.critical("RESPONSE: " + str(r.json()))
	return r.json()["result"]["message_id"]

def send_photos(post): #used to send multiple photos in a chain of replies
	photos=post["photos"]
	post["photo"]=photos[0]
	reply_id=send_photo(post)
	photos=photos[1::]
	for photo in photos:
		post["text"]=""
		post["photo"]=photo
		post["reply_id"]=reply_id
		reply_id=send_photo(post)

# content handling
# jesus facebook is fuc*ing awful

def handle_text(post):
	text=handle_shares(post)
	#here it's handling the text
	text_area=post.select_one("div._5pbx.userContent")
	if text_area:  # here it's detected if it is there
		# hiding elements for long posts are detected
		useless_texts=text_area.find_all(class_="text_exposed_hide")
		for junk in useless_texts:
			junk.decompose()  # and eleminated
		wall_text=text_area.find(class_="text_exposed_link") #still have to find a way to handle Continue reading links
		strings=text_area.find_all(string=re.compile("[<>&]"))
		for string in strings:
			string.replace_with(str(cgi.escape(string))) #here link are recompiled as text so they can be read later and can be understood by Telegram
		profile_links=text_area.find_all("a", class_="profileLink")
		for profile in profile_links:
			profile.string.replace_with(str(profile)) #same thing for Facebook Profile Links
		text=text+text_area.get_text()  # the text is then extraced from the HTML code
		return text
	else:
		return ""

def handle_shares(post):
	try:
		share_area=post.select_one("span._1nb_.fwn")
		shared_page_link, shared_page=share_area.a["href"], share_area.a.string
		link="\U0001F4E4 <a href="+str(shared_page_link)+">"+str(shared_page)+"</a>/n"
		text=str(share_area.next_sibling_next_sibling.get_text())
		text=str(link)+str(text)+"/n /n"
		return str(text)
	except:
		return ""

def find_photo(post):
	# the area of the posts that handles a single photo is identified with the unique class
	photo_area=post.find("div", class_="_5cq3")
	if photo_area:  # here it's checked if it's really there
		photo=photo_area.find("img")  # the <img> tag is extrapolated
		# the link to the photo at the origin is extrapolated from the tag
		photo_link=photo["src"]
		return photo_link
	else:  # handling in case there is another type of photo in this post
		photo_area=post.find("div", class_="_517g")
		if photo_area:  # here it's cheked if it's really there
			photo=photo_area.find("img")  # the <img> tag is extrapolated
			# the link to the photo at the origin is extrapolated from the tag
			photo_link=photo["src"]
			return photo_link
		else:  # handling in case there is no photo in this post
			return None

def find_photos(post): #basically the same as find_photo but with different tags for multiple photo posts
	photos=[]
	multi_photo_area=post.find("div", class_="_2a2q")
	if multi_photo_area:
		photo_areas=multi_photo_area.find_all("a")
		for photo_area in photo_areas:
			try:
				photo_link=photo_area["data-ploi"]
			except KeyError:
				return None
			photos.append(photo_link)
		return photos
	else:
		return None

def parsing_link(query, FB_link): #used to get around Facebook's secure link
	try:
		if query["u"] != "":
			link=str(query["u"][0])
			return link
	except KeyError:
		link=str(FB_link)
		return link

def link_parse(FB_link): #used to parse a link out of Facebook's secure logout
	parsed_FB_link=urlparse(FB_link)
	query=parse_qs(parsed_FB_link.query)
	return parsing_link(query, FB_link)

def find_link(post): #used to find the main link in link posts
	link_area=post.find("a", class_="_52c6")  # this is for majority of link posts
	if link_area:
		FB_link=link_area["href"]
		link=link_parse(FB_link)
		return link
	else:
		#for Youtube, twitch and other video links detected by FB
		link_area=post.find("div", class_="mbs _6m6 _2cnj _5s6c")
		if link_area:
			# facebook hides the shared link with it's own "secure logout"
			FB_link=link_area.a["href"]
			link=link_parse(FB_link)
			return link
		else:
			return None

def has_video(post): #to detetc of a post has a Facebook video
	split_link2post=list(post["link2post"].split('/'))
	try:
		if split_link2post[4] == "videos":
			return True
	except:
		return False

def find_video(post):
	# facebook mobile has plain link to the videos on their servers so i can strip them and use those directly
	mobile_URL=post["link2post"][:8:] + "m" + post["link2post"][11::]
	soup=BeautifulSoup(get_url(mobile_URL), "html.parser")
	video_areas=soup.find_all("a", target="_blank")
	if video_areas != [] and video_areas != None:
		for video_area in video_areas:
			if video_area.contents[0].name != "span":
				video_link_dict=parse_qs(video_area["href"])
				print("VIDEO DICT: " + str(video_link_dict))
				if "/video_redirect/?src" in video_link_dict:
					video_link=video_link_dict["/video_redirect/?src"]
				elif "https://lm.facebook.com/l.php?u" in video_link_dict:
					video_link=video_link_dict["https://lm.facebook.com/l.php?u"]
				return video_link[0]
			continue
	return -1  # lives do have /videos/ in the URL but don't have a target _blank, to catch this possibility it returns -1

def handle_link2post(post): #to generate the link to the Facebook post
	link2post_area=post.find("span", class_="fsm fwn fcg")
	try:
		link2post="https://www.facebook.com" + link2post_area.a["href"]
		return link2post
	except:
		return ""

def content(post): #used to detect and handle the different kinds of posts and contents
	post["text"]=handle_text(post)
	post["text"]=add_link2post(post)
	logging.debug("Basic text handled!")
	if find_photo(post):
		post["photo"]=find_photo(post)
		post["first_photo"]=True
		post["no_link"]=True
		post["text"]=add_page_name(post)
		logging.debug("Prepared the photo post")
		send_photo(post)
	elif find_link(post):
		post["link"]=find_link(post)
		post["text"]=add_link(post)
		post["text"]=add_page_name(post)
		logging.debug("prepared the link post")
		send_post(post)
	elif find_photos(post):
		post["photos"]=find_photos(post)
		post["no_link"]=True
		post["text"]=add_page_name(post)
		logging.debug("Prepared the multiple photo post")
		send_photos(post)
	elif has_video(post):
		post["video"]=find_video(post)
		post["no_link"]=True
		if post["video"] != -1:  # if it's -1 then there was no video link and so it is send like a normal text post
			post["text"]=add_video_link(post)
			post["no_link"]=False
			logging.debug("Found the video")
		post["text"]=add_page_name(post)
		logging.debug("Posting the video")
		send_post(post)
	else:
		post["no_link"]=True
		post["text"]=add_page_name(post)
		logging.debug("Sending the post")
		send_post(post)

def new_posts_handling(posts, last_time, bot, channel_ID, page_name): #here it's checked of there are new posts
	logging.debug("Last valid time: " + str(last_time))
	times=[int(last_time)]
	for post in posts:
		post_time=get_post_time(post) #the Unix time is gathered
		if int(post_time) > int(last_time):
			logging.debug("New post with post_time: " + \
			              str(post_time) + " for " + str(page_name))
			post["BOT"], post["channel_ID"], post["page_name"]=bot, channel_ID, page_name
			content(post) #the post is handled
			times.append(int(post_time)) #the new post time is added to the list
			logging.debug("Appended new post time: " + str(post_time))
	return max(times) #the new top post time is returned

def gather_data(input_file): #pages are loaded for the input file
	pages=[]
	try:
		with open(input_file, "r", newline='', encoding='utf_8') as file:
			next(file, None)
			reader=csv.reader(file)
			pages=list(reader)
		logging.info("PAGES: " + str(pages))
	except IOError:
		logging.warning("No input file was found at " + input_file)
	return pages

def main():
	args=argument_parser() #command line arguments
	numeric_level=getattr(logging, args["debug_LVL"].upper(), None)
	if not isinstance(numeric_level, int):
		raise ValueError("Invalid log level in command line: " + args["debug_LVL"])
	logging.basicConfig(filename=args["log_file"], level=numeric_level)
	input_file=args["input_file"]
	logging.info("LOADED INPUT FILE: " + args["input_file"])
	try:
		while True: #the main loop
			pages=gather_data(input_file)
			for page in pages:
				#[0]is HUMAN REDABLE data, [1] is NAME, [2] is URL, [3] is LAST_TIME, [4] is TOKEN and [5] is ID
				page_name=page[1]
				logging.info("HUMAN DATA: " + page[0])
				logging.info("SHOWN ON CHANNEL: " + page_name)
				URL=page[2]
				logging.info("PAGE URL: " + URL)
				TOKEN=page[4]
				channel_ID=page[5]
				last_time=page[3]
				data=get_url(URL)
				soup=BeautifulSoup(data, "html.parser")
				posts=soup.find_all("div", "_427x") # seems to be hardcoded in FB's HTML code to define posts
				posts.reverse()
				page[3]=new_posts_handling(posts, last_time, TOKEN, channel_ID, page_name)
				update_csv(pages, input_file)
			date=get_date()
			logging.info("Now sleeping, Time: " + date)
			time.sleep(600)
	except Exception as e:
		logging.critical("ERROR AT " + get_date() + "\nERROR INFO:" + str(e))

if __name__ == '__main__':
	main()
