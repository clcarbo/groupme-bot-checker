'''
This is the heart of the bot; it's how it handles requests.
Flask lets us use a WSGI server to respond to TCP/IP requests
in a meaninful way. This lets the bot be alerted when the
chat is being used and tells it what functions to call
when certain behaviors are followed.
'''

from flask import Flask, request
import os
import requests
import re
import fishing
import random
import time
from multiprocessing import Process, active_children

# Instantiate a Flask object
app = Flask(__name__)

# Define the only route for the server
@app.route('/', methods=['POST'])
def checkit():
    '''The only route for the app. Respond to post requests sent to the endpoint.'''
    #---------------------#
    #-- Handle the ping --#
    #---------------------#
    # Parse the message JSON
    post = request.get_json()
    # Ignore posts by the bot
    if post['name'] == 'checkers' or post['name'] == 'testBot':
        return 'The End.'

    # Default response does not exist
    response = None


    #----------#
    #-- Help --#
    #----------#
    if post['text'].lower() == '!help':
        response = 'Hey! I\'m checkers, the bot that hopes you check yourself before your wreck yourself. The following commands are available:\n!help: See this message\n!insult <name>: Generate an insult\n!loaves: Get bread facts\n!gofish [<location>][<boat>]: Go fishing in an optionally specified location and boat (if unspecified, a random boat and location are chosen for you based on your skill)\n!fish: Learn more about the fishing minigame'

    #---------------------#
    #-- Loaves behavior --#
    #---------------------#
    # Get a bread fact and return it
    elif post['text'].lower() == '!loaves':
        from loaves import breadfacts
        response = breadfacts()


    #-------------#
    #-- Fishing --#
    #-------------#

    # Commands for going fishing ---------------------------------------
    elif re.search('^!gofish', post['text'].lower()):
        if int(post['user_id']) in fishing.fetchCurrentFishers():
            # If already fishing, don't fish and tell them they're fishing
            response = "You're already fishing. Kick back and {}"\
                .format(random.choice(fishing.ACTIVITIES))
        else:
            #-------------------------------#
            #-- Otherwise, invoke fishing --#
            #-------------------------------#
            # Get the player's data
            user_data = fishing.getUser(post['user_id'])

            # Check if they specified a location
            hab = re.search("|".join(fishing.HABITATS_SET).lower(),
                            post['text'].lower())
            # If no location was specified, pick a random one which they can
            # visit when considering their available boats
            hab = hab[0].title() if hab else fishing\
                .pickViableHabitat(user_data[2])

            # Check if they specified a boat
            boat = re.search("|".join([boat[0] for boat in fishing.BOATS]),
                             post['text'].lower())
            # If they did not, pick their best boat.
            boat = boat[0] if boat else fishing.BOATS[user_data[2] - 1][0]

            # Add them to the table of current fishers
            delay = fishing.addCurrentFisher(post['user_id'], hab, user_data[1])
            fish = fishing.goFishing(hab, boat, user_data[2], user_data[1])

            # Check for improper input (this is an ugly way of doing this)
            if fish in { "You can't use this boat yet.",
                         "Your boat isn't well suited to fishing in this location."}:
                response = fish
                fishing.resetFishingStatus(post['user_id'])
            else:
            # Start the process to resolve the fishing trip
                Process(target=fishing.resolveFisher,
                        args=(fish, user_data[0], hab, delay, user_data[2], user_data[1]),
                        name=f"Process-{user_data[0]}")\
                    .start()

            # Send a response to acknowledge that your request was handled.
                response = "You cast out your line. Kick back and {}"\
                    .format(random.choice(fishing.ACTIVITIES))

    # Commands for fishing data -----------------------------------------
    elif re.search('^!fish', post['text'].lower()):

        # Command for reseting fishing status
        if re.search('retry', post['text'].lower()):
            temp_id = post['user_id']
            try:
                process_to_kill = [p for p in active_children()
                               if p.name == f"Process-{temp_id}"][0]
                process_to_kill.terminate()
            except:
                pass

            fishing.resetFishingStatus(post['user_id'])
            response = "You reel in your line to try again."

        elif re.search("locations", post['text'].lower()):
            response = fishing.getInfo('habs')

        # Commands for info about boats and rods
        elif re.search('boats|rods', post['text'].lower()):
            response = fishing.getInfo(re.search('boats|rods',
                                                 post['text'].lower())[0])

        # Commands for info about locations
        elif re.search("|".join(fishing.HABITATS_SET),
                       post['text'].title()):
            response = fishing.getInfo(re.search("|".join(fishing.HABITATS_SET),
                                                 post['text'].title())[0])

        # Commands for leaderboard stats
        elif re.search("leaderboard", post['text'].lower()):
            response = fishing.getInfo("leaderboard")

        # Commands for user data
        elif re.search("lstats", post['text'].lower()):
            response = fishing.getInfo('lstats', post['user_id'])

        elif re.search("stats", post['text'].lower()):
            response = fishing.getInfo(user_id=post['user_id'])

        else:
            response = "Welcome to the fishing minigame! The following commands are available:\n\nReset:\n--------------\n!fish retry: Reel in your line to try again\n\nInfo:\n--------------\n!fish locations: See the available locations for fishing\n!fish boats: Learn more about the different boats available\n!fish rods: Learn more about the different kinds of rods available\n!fish <location>: Learn more about the specified locations\n\nScores\n--------------\n!fish leaderboard: View the leaderboards\n!fish stats: see your individual stats\n!fish lstats: see your individual stats by location"


    #--------------------------#
    #-- Sending the response --#
    #--------------------------#
    if response:
        # Put the parameters together
        data = {'bot_id': os.environ['bot_id'],
                'text': response}
        # Send the post request to the group
        r = requests.post('https://api.groupme.com/v3/bots/post', data=data)
    # Return a placeholder string to appease Flask
    return 'Nice!'


if __name__ == '__main__':
    app.run(port=5000)
