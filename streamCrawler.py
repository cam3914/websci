import nltk
from nltk.corpus import wordnet
import tweepy
import json
from pymongo import MongoClient
from datetime import datetime
import time
import sys
import emoji
import re
from nltk.corpus import words

#  please put your credentials below - very important
consumer_key = "A90...svwKtl"
consumer_secret ="beWev2TLi3MR...xP0NWUYYZX7"
access_token ="1620524185-VC9Yw8...8nIs0M0pgMYUZn"
access_token_secret ="GJ9eUiAMhT...imE0uPa8azwRV"

nltk.download([
    "words",
    "wordnet",
])

# Seed words
emotion_categories = ["excitement", "happy", "pleasant", "surprise", "fear", "anger"]

# Wordnet synonyms
for category in emotion_categories:
    synonyms = []
    for syn in wordnet.synsets(category):
        for l in syn.lemmas():
            synonyms.append(l.name())
    print(set(synonyms))
    
# final seed words
seed_words = {}
seed_words['excitement'] = ["excited", "excitement"]
seed_words['happy'] = ["happy", "happiness", "glad"]
seed_words['pleasant'] = ["pleasant", "pleased", "delight", "proud", "love"]
seed_words['surprise'] = ["sad", "frustration", "frustrated"]
seed_words['fear'] = ["fear", "disgust", "depressed", "fright", "dread", "concern"]
seed_words['anger'] = ["anger", "angry", "furious", "raging"]

# emoticons
emoticons = {}
emoticons['excitement'] = [":D", ":O", ":0", "0:", "O:", ":-D", ":-O", ":-0", "0-:", "O-:"]
emoticons['happy'] = [":)", "(:", ":-)", "(-:"]
emoticons['pleasant'] = ["<3", ";)"]
emoticons['surprise'] = [":(", ":|", ":/", "):", "|:", "\:",]
emoticons['fear'] = [":(", "):"]
emoticons['anger'] = [">:(", "):<", ">_<"]

complete_seed_words = seed_words['excitement'] + seed_words['happy'] + seed_words['pleasant'] + seed_words['surprise'] + seed_words['fear'] + seed_words['anger']
complete_emoticon_list = emoticons['excitement'] + emoticons['happy'] + emoticons['pleasant'] + emoticons['surprise'] + emoticons['fear'] + emoticons['anger'] 


auth = tweepy.OAuthHandler(consumer_key, consumer_secret )
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)
if (not api):
    print('Can\'t authenticate')
    print('failed cosumeer id ----------: ', consumer_key )
# set DB DETAILS


# this is to setup local Mongodb
client = MongoClient('127.0.0.1',27017) #is assigned local port
dbName = "TwitterDump" # set-up a MongoDatabase
db = client[dbName]
collName = 'rawTweets' # here we create a collection
collection = db[collName] #  This is for the Collection  put in the DB


# function to remove duplicated letters at given index
def make_single(chars, index):
    new_chars = chars[:index + 1]
    complete = False
    
    for i in range(index + 1, len(chars) - 1):
        if not complete:
            if chars[i] == chars[i + 1]:
                continue
            else:
                new_chars.append(chars[i + 1])
                complete = True
        else:
            new_chars.append(chars[i + 1])
            
    return "".join(new_chars)

# function to remove duplicated letters at given index, leaving double letters
def make_double(chars, index):
    new_chars = chars[:index + 2]
    complete = False
    

    for i in range(index + 1, len(chars) - 1):
        if not complete:
            if chars[i] == chars[i + 1]:
                continue
            else:
                new_chars.append(chars[i + 1])
                complete = True
        else:
            new_chars.append(chars[i + 1])
            
    return "".join(new_chars)

# function to find indicies of multiple letters in word
def get_multiples_indicies(chars):
    indicies = []
    newLetter = True
    for i in range(0, len(chars) - 1):
        if chars[i] == chars [i + 1]:
            if newLetter:
                indicies.append(i)
                newLetter = False
        else:
            newLetter = True

    return indicies

def expand_word(word):
    return word[:-3] + " not"
    

def verify_word(x):
    # remove links
    if x.startswith("https"):
        return ""
    # expand contractions
    elif x not in words.words() and (x[-3:] == "n't" or x[-3:] == "n’t"):
        return expand_word(x)
    # check for duplicated letters
    elif x not in words.words():
        chars = list(x)
        indicies = get_multiples_indicies(chars)
        
        if len(indicies) == 0:
            return x
        if len(indicies) == 1:
            singles = make_single(chars, indicies[0])
            doubles = make_double(chars, indicies[0])
            if singles in words.words():
                return singles
            elif doubles in words.words():
                return doubles
            else:
                return x 
        
        # special case of 2 different duplicated letters
        if len(indicies) == 2:
            ## both single
            chars1 = list(make_single(chars, indicies[0]))
            word1 = make_single(chars1, get_multiples_indicies(chars1)[0])
            ## single then double
            chars2 = list(make_single(chars, indicies[0]))
            word2 = make_double(chars2, get_multiples_indicies(chars2)[0])
            ## double then single
            chars3 = list(make_double(chars, indicies[0]))
            word3 = make_single(chars3, get_multiples_indicies(chars3)[1])
            ## double then double
            chars4 = list(make_double(chars, indicies[0]))
            word4 = make_double(chars4, get_multiples_indicies(chars4)[1])
            

            if word1 in words.words():
                return word1
            elif word2 in words.words():
                return word2
            elif word3 in words.words():
                return word3
            elif word4 in words.words():
                return word4
            else:
                return x 
    else:
        return x

def strip_emoji(text):
    #  copied from web - don't remeber the actual link
    new_text = re.sub(emoji.get_emoji_regexp(), r"", text)
    return new_text

def cleanList(text):
    #  copied from web - don't remeber the actual link
    #remove emoji it works
    text = strip_emoji(text.lower())
    text.encode("ascii", errors="ignore").decode()
    newstring = []
    for word in text.split():
        verified = verify_word(word)
        newstring.append(verified)
        
    return " ".join(newstring)

def hashtag_classification(split_text):
    not_hashtag = True
    hashtags = []
    labels = ["excitement", "happy", "pleasant", "surprise", "fear", "anger"]
    classifications = [0,0,0,0,0,0]
    classification = -1
    i = -1
    
    # find all hashtags at end of text
    while not_hashtag:
        if split_text[i].startswith('#'):
            hashtags.append(split_text[i][1:])
            i -= 1
        else:
            not_hashtag = False
        
    # classify found hashtags
    for hashtag in hashtags:
        for i, label in enumerate(labels):
            if hashtag in seed_words[label]:
                classifications[i] += 1
                classification = i
                # check if there are conflicting hashtags
                if sum(classifications) != classifications[i]:
                    return -1
    
    return classification

    
def emoticon_classification(split_text):
    labels = ["excitement", "happy", "pleasant", "surprise", "fear", "anger"]
    classifications = [0,0,0,0,0,0]
    classification = -1
    
    # classify emoticons
    for string in split_text:
        for i, label in enumerate(labels):
            if string in emoticons[label]:
                classifications[i] += 1
                classification = i
                # check if there are conflicting hashtags
                if sum(classifications) != classifications[i]:
                    return -1
    
    return classification
    

def processTweets(tweet):
    #  this module is for cleaning text and also extracting relevant twitter feilds
    # initialise placeholders
    labels = ["excitement", "happy", "pleasant", "surprise", "fear", "anger"]

    # Pull important data from the tweet to store in the database.
    try:
        created = tweet['created_at']
        tweet_id = tweet['id_str']  # The Tweet ID from Twitter in string format
        text = tweet['text']  # The entire body of the Tweet
    except Exception as e:
        # if this happens, there is something wrong with JSON, so ignore this tweet
#         print(e)
        return None

    try:
        # // deal with truncated
        if(tweet['truncated'] == True):
            text = tweet['extended_tweet']['full_text']
        elif(text.startswith('RT') == True):
            # print(' tweet starts with RT **********')
            return None

    except Exception as e:
        print(e)
        
    #initialize classifications, -1 for no category
    hashtag_class = -1
    emoticon_class = -1
    final_class = -1
    
    # check ends with hashtag
    split_text = text.lower().split()
    if split_text[-1].startswith("#"):
        hashtag_class = hashtag_classification(split_text)
        
    emoticon_class = emoticon_classification(split_text)
                
    if hashtag_class == -1 and emoticon_class == -1:
        return None
    elif hashtag_class == -1 and emoticon_class != -1:
        final_class = emoticon_class
    elif hashtag_class != -1 and emoticon_class == -1:
        final_class = hashtag_class
    elif hashtag_class == emoticon_class:
        final_class = hashtag_class
    else:
        return None
    
    # Clean text    
    text = cleanList(text)
   
    tweet1 = {'_id' : tweet_id, 'date': created, 'text' : text, 'class': labels[final_class]}
    print("classified: " + tweet1['class'])

    return tweet1

class StreamListener(tweepy.StreamListener):
  #This is a class provided by tweepy to access the Twitter Streaming API.

    global geoEnabled
    global geoDisabled
    def on_connect(self):
        # Called initially to connect to the Streaming API
        print("You are now connected to the streaming API.")

    def on_error(self, status_code):
        # On error - if an error occurs, display the error / status code
        print('An Error has occured: ' + repr(status_code))
        return False

    def on_data(self, data):
        #This is where each tweet is collected
        # let us load the  json data
        t = json.loads(data)
        #  now let us process the tweet so that we will deal with cleaned and extracted JSON
        tweet = processTweets(t)

        # now insert it
        #  for this to work you need to start a local mongodb server
        if tweet:
            try:
                collection.insert_one(tweet)
            except Exception as e:
                print(e)
#                 this means some Mongo db insertion errort



#Set up the listener. The 'wait_on_rate_limit=True' is needed to help with Twitter API rate limiting.

# WORDS = ['manhattan' , 'new york city', 'statue of liberty']
# LOCATIONS = [ -75,40,-72,42] # new york city
Loc_UK = [-10.392627, 49.681847, 1.055039, 61.122019] # UK and Ireland
Words_UK =["Boris", "Prime Minister", "Tories", "UK", "London", "England", "Manchester", "Sheffield", "York", "Southampton", \
 "Wales", "Cardiff", "Swansea" ,"Banff", "Bristol", "Oxford", "Birmingham" ,"Scotland", "Glasgow", "Edinburgh", "Dundee", "Aberdeen", "Highlands", \
"Inverness", "Perth", "St Andrews", "Dumfries", "Ayr", \
"Ireland", "Dublin", "Cork", "Limerick", "Galway", "Belfast"," Derry", "Armagh", \
"BoJo", "Labour", "Liberal Democrats", "SNP", "Conservatives", "First Minister", "Sturgeon", "Chancelor", \
"Boris Johnson", "BoJo", "Keith Stramer"]

print("Tracking: " + str(Words_UK))
#  here we see the listener object
listener = StreamListener(api=tweepy.API(wait_on_rate_limit=True))
streamer = tweepy.Stream(auth=auth, listener=listener)
streamer.filter(locations=Loc_UK, track=Words_UK, languages = ['en'], is_async=False, stall_warnings=True)
