#import libraries
import csv, json
import requests, random
from time import sleep
import time
import tweepy
import os
import string
import subprocess
import locale

#establish keys as global variables
secret_keys = []
consumer_key = 'KixchowUQDXKrWBwqpuQyEtXW'
access_token = '4851145943-CG7jPXvHhSfGSWgTBALJL55tjpvqS8On7jXZkgU'
template = ['{0} has spent ${1} on this "{2}" ad on {3} issues +{4}',
'{0} has spent ${1} on this "{2}" ad +{4}']
#hacky fix to solve unpredictable locale problems
try:
	locale.setlocale(locale.LC_ALL, 'en_US.utf8')
except:
	locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

#global vars
tweet_status = ''
img_dest = 'img/'
data_dest = 'data/'

#Our main worker function
def main():
	generate_tweet()
	tweet_status = generate_tweet()
	tweet(tweet_status)

def generate_tweet():
	campaign_totals = 'campaign_totals.csv'

	#Get the number of lines in the CSV
	with open(data_dest + campaign_totals,'rU') as csv_input:
		reader = csv.reader(csv_input)
		row_count = sum(1 for line in reader)
	# open csv
	with open(data_dest + campaign_totals,'rU') as csv_input:
		reader = csv.reader(csv_input)
		#get a list of fields with indexes
		csv_fields = {}
		i = 0
		for field in reader.next():
			csv_fields[i] = field
			i+=1
		j = 0
		# select random line
		rand = random.randint(0, row_count-2)
		while j < rand:
			reader.next()
			j += 1
		# read in csv values and use schema to select columns
		for row in reader:
			#for testing
			#cleaning up title
			group = row[2]
			if ',' in group:
				group = " ".join(group.split(", ")[::-1])

			tw_temp = template[0]
			if row[4] == '':
				tw_temp = template[1]
			no_spaces = 1
			if '/NC' in row[0]:
				no_spaces = 2
			return tw_temp.format(
				group.title(), #group
				locale.format('%d',int(row[1]),grouping=True), #money
				(row[0].split(" ",no_spaces)[-1]).title(), #ad name
				row[4], #issue type, if it exists
				row[6]
				)
			break

def process_video(video_url):
	#check if the gif exists already
	file_name = video_url.rsplit('/', 1)[-1]
	stored_file = img_dest + file_name
	if os.path.isfile(stored_file.rsplit('.wmv',1)[0]+'.gif'):
		print 'GIF already created. Skipping video download...'
		return stored_file.rsplit('.wmv',1)[0]+'.gif'
	else:
		#download the image. we should delete this later because we won't need it
		print 'Getting video at',video_url
		try:
			r = requests.get(video_url, stream=True)
			print 'Saving file to',stored_file
			with open(stored_file, 'wb') as f:
				f.write(r.content)
			#construct the ffmpeg command
			command = ('ffmpeg -y -i {0}{1}.wmv -filter:v "setpts=0.25*PTS" -vf fps=2,scale=400:-1:flags=lanczos,palettegen palette.png && '
				'ffmpeg -i {0}{1}.wmv -i palette.png -filter_complex "setpts=0.25*PTS,fps=2,scale=400:-1:flags=lanczos[x];[x][1:v]paletteuse" {0}{1}.gif'
				).format(img_dest,file_name.rsplit('.wmv',1)[0])
			subprocess.Popen([command], shell=True, stdout=subprocess.PIPE).stdout.read()

			return stored_file.rsplit('.wmv',1)[0]+'.gif'
		except requests.exceptions.RequestException as e:
			print 'Error:',e
			return 'error'

def tweet(twitter_msg):
	#parse message parameter
	update = twitter_msg.split('+',1)[0]
	gif_url = twitter_msg.split('+',1)[1]

	gif_file = process_video(gif_url)

	#generate auth details
	_get_secrets()
	auth = tweepy.OAuthHandler(consumer_key, secret_keys[0])
	auth.set_access_token(access_token, secret_keys[1])

	#create tweepy object
	api = tweepy.API(auth)

	update = _shorten(update)

	print update
	print "Tweet length:",len(update)

	#attempt to update twitter with given status
	#need options for cleaning up input and shortening when len(update) is > 140
	#check length of tweet
	#with gif, link, hashtag = 85
	#with gif, hashtag = 109
	#with link, hashtag = 110
	#with hashtag = 134
	#need to add 'wral.com/15183674 ' to update below

	try:
		if gif_file != "error":
			if len(update) <= 85:
				update = update+'#ncpol'
				#update = update+'wral.com/15183674 #ncpol'
			elif len(update) <= 109:
				update = update+'#ncpol'
			api.update_with_media(gif_file,update)
			print update
			print 'Tweet sent with media at', time.asctime(time.localtime(time.time()))
		else:
			if len(update) <= 110:
				update = update+'#ncpol'
				#update = update+'wral.com/15183674 #ncpol'
			elif len(update) <= 134:
				update = update+'#ncpol'
			api.update_status(update)
			print update
			print 'Tweet sent with media at', time.asctime(time.localtime(time.time()))
	except tweepy.TweepError, e:
		print 'Error sending tweet:', e[0][0]['message']
		print 'Logged at', time.asctime(time.localtime(time.time()))

#utility function for retrieving secret keys
def _get_secrets():
	global secret_keys
	with open('.keys') as f:
		secret_keys = f.read().splitlines()

#utility function for attempting to shorten an update
def _shorten(long_tweet):
	short_tweet = long_tweet
	short_tweet = string.replace(short_tweet," Pac "," ",1)
	short_tweet = string.replace(short_tweet,"North Carolina","NC",1)
	short_tweet = string.replace(short_tweet," Nc "," NC ",1)
	short_tweet = string.replace(short_tweet,".","")
	short_tweet = string.replace(short_tweet," Usa "," ")
	short_tweet = string.replace(short_tweet,"National","Ntl")
	short_tweet = string.replace(short_tweet,"Association","Assn")
	short_tweet = string.replace(short_tweet,"Partnership","Pship")
	short_tweet = string.replace(short_tweet,"Foundation","Fnd")
	return short_tweet

if __name__ == '__main__':
	print 'Generating tweet ...'
	main()