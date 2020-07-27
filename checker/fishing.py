'''
Module for the groupme fishing minigame.
'''

import pickle
import psycopg2
import re
import statistics as stats
import random
import math
import time
import requests
import asyncio
import os

#-------------------------------#
#-- Defining module constants --#
#-------------------------------#

DATABASE_URL = os.environ['DATABASE_URL']

LEVEL_CHECKS = {'rod':(
    (1, 5, "After catching 5 different kinds of fish, the regulars at {}'s local bass pro shop no longer view them with contempt. The employees agree to sell them a fiberglass fishing rod. They should have fewer problems when attempting to catch fish in the future."),
    (2, 15, "After catching 15 different kinds of fish, an impressed bass pro regular recommends a carbon fiber rod to {}. They shouldn't have to worry about their line snapping as much."),
    (3, 30, "After catching 30 different kinds of fish, one of the regulars suggests another, less well-known fishing shop to {}. They have to use a password to get in. The owner, impressed by their accomplishments, recommends a hand-crafted bamboo rod. It should make catching big fish easier."),
    (4, 50, "After hauling in 50 species of fish, a homeless man calls {0} over upon their return to land. His skin is tan and his hair is long; he has a regal look about him. He hands {0} a glowing fishing rod which seems to be perpetually changing color. Without a word, he vanishes into the sea.")),
                'boat':(
                    (1, 100, "After catching over 100lbs of fish, {} decides to invest in a dingy. It's still small, but at least there's some leg room. They can now participate in Lake and Nearshore fishing."),
                    (2, 300, "After catching over 300lbs of fish, {} decides to purchase a swamp boat. Its flat underside is more stable than the dingy and should make catching bigger fish easier."),
                    (3, 750, "After catching over 750lbs of fish, {} invests in a bass boat. Bask in the feeling of accomplishment. The seats on the boat have places to secure your fishing rod, decreasing the likelihood of something going wrong when trying to reel in a fish."),
                    (4, 1500, "Upon catching over 1,500lbs of fish, {} finds they have saved up enough money to purchase a skipper. Offshore fishing is finally possible. Big game fish are finally on the menu. Good luck!")
                )}

BOATS = (('kayak', 0,
          'Not too stable. Good for rivers, flats, and backcountry fishing, but not for big bodies of water. Your starting boat.'),
         ('dingy', 30,
          f'More stable than a kayak, but still pretty small. Allows for lake and nearshore fishing. Unlocked by catching over {LEVEL_CHECKS["boat"][0][1]}lbs of fish.'),
         ('swamp boat', 60,
          f'Propelled by a fan. Good for backcountry and flats fishing. Unlocked by catching over {LEVEL_CHECKS["boat"][1][1]}lbs of fish.'),
         ('bass boat', 80,
         f'The end goal for most casual fishers. Comes with cupholders. Perfect for lake, inshore, reef, and river fishing. Unlocked by catching over {LEVEL_CHECKS["boat"][2][1]}lbs of fish.'),
         ('skipper', 95,
         f'The "reel" fucking deal. The American dream incarnate. The only boat that allows for offshore fishing. Baby, you could catch a shark on this thing. Unlocked by catching over {LEVEL_CHECKS["boat"][3][1]}lbs of fish.'))

BOAT_LEVELS ={'kayak': 1, 'dingy': 2, 'swamp boat': 3, 'bass boat': 4, 'skipper': 5}

RODS = (('driftwood and string', 0,
         'It\'s a bit fragile, but it will get the job done. Your starting fishing rod.'),
        ('fiberglass', 30,
        f'Stronger than driftwood, but a bit impersonal. Still not designed for large fish. Unlocked by catching {LEVEL_CHECKS["rod"][0][1]} different species of fish.'),
        ('carbon fiber', 60,
        f'Good for bigger fish. A standard among red-necks. Unlocked by catching {LEVEL_CHECKS["rod"][1][1]} different species of fish.'),
        ('hand-crafted bamboo', 85,
        f'A rod for people who appreciate the artwork of fishing. Slightly increases the likelihood of you catching a fish. Unlocked by catching {LEVEL_CHECKS["rod"][2][1]} different species of fish.'),
        ('"the God Rod"', 98,
        f'Nobody knows what material comprises this rod. It seems to be glowing slightly. Increases the likelihood of you catching a fish. Unlocked by catching {LEVEL_CHECKS["rod"][3][1]} different species of fish.')
        )

HABITATS_SET = {'Backcountry', 'Flats',
                'Inshore', 'Lake',
                'Nearshore', 'Offshore',
                'Reef', 'River', 'Wreck'}

TOPIC_ADJ = ("stupid", "nice", "silly",
             "fun", "dumb", "scintillating",
             "insightful", "meandering", "long-winded",
             "goofy", "insipid", "innocuous",
             "lively", "quaint", "enthusiastic",
             "thoughtful", "enlightening", "confusing"
            )

HABITATS_AVG_LB = {'Flats': {'size': 23.505147154761904,
                             'level': 1,
                             'description': "A flat is any long, level, and shallow area in a body of water. You’ll find flats in freshwater as well as saltwater, consisting of sand, mud, rocks, or grass. Flats fishing is all about casting lines in the world’s shallowest waters. Gamefish large and small make their way onto the flats, sometimes swimming in water just several inches deep.\n\nFlats are a nice, easy place to start fishing."},
                   'Reef': {'size': 18.454623,
                            'level': 4,
                            'description': "Reefs are permanent underwater structures, usually consisting of rock or coral, where a variety of species find shelter and food. The most prevalent techniques anglers use while reef fishing include bottom fishing, jigging, and drift fishing (since anchoring can cause damage to living reefs).\n\nYou may not find many large fish in the reefs, but the high catch rate ensures you'll catch a lot of smaller ones."},
                   'Inshore': {'size': 29.84895825,
                               'level': 4,
                               'description': "Inshore fishing means something a little different everywhere you go. This term generally includes waters just off the beach, extending to around 10 or 20 miles offshore. In addition to a variety of Snappers and Groupers, anglers can expect to catch Mackerel, Amberjack, Sharks, and Cobia.\n\nCatch rates are slightly lower than average, but you can catch some large fish while inshore fishing."},
                   'Wreck': {'size': 16.61736268,
                             'level': 2,
                             'description': "Wreck fishing is all about making the most of vehicles that have made their way to the bottom of the sea. This includes ships, boats, planes, submarines, and much more. No matter where you happen to find a wreck, it’s bound to be the source of outstanding fishing.\n\nFish who make their homes in wrecks tend to be small, but you're almost guaranteed to catch them."},
                   'Lake': {'size': 24.238839284090908,
                            'level': 2,
                            'description': "When people think of fishing, many of them picture a day on the lake. It's a classic fishing location; what more can you ask for?\n\nLakes provide a nice balance between the rate of catching fish and the size of fish available."},
                   'Backcountry': {'size': 22.99683214,
                                   'level': 1,
                                   'description': "Backcountry fishing has a different meaning depending on where you fish. In south Florida and the Keys, this applies to inshore islands and flats like those found in Everglades National Park. In other parts of the world, fishing the backcountry means hiking mountains and casting a line in gin-clear streams. No matter where you’re fishing and what the local backcountry might be, you can look forward to exploring untouched wilderness and secret waterways.\n\nThe backcountry is a good solution for those who want to catch large fish without sacrificing their catch rate."},
                   'River': {'size': 22.141528468867925,
                             'level': 1,
                             'description': "Trout, Salmon, Arapaima, Walleye, Bass, Tarpon, Barramundi, Catfish, Carp, Tigerfish, Crappie, Perch, Dolly Varden, Muskellunge, Pike... you never know what you'll catch in a river. Species vary greatly from region to region, so fishing your local river will be a completely different experience than one several hundred miles away.\n\nRiver's have both a good catch rate and good average size of fish."},
                   'Nearshore': {'size': 22.213362101973683,
                                 'level': 2,
                                 'description': "Nearshore fishers rarely find themselves more than 10 miles from shore, usually in water that ranges from several inches to roughly 20 feet deep. Of course, these numbers vary widely depending on the location, as do the fish you can expect to catch.\n\nNearshore fishing is good for those who want to catch decently sized fish quickly."},
                   'Offshore': {'size': 75.5247039516129,
                                'level': 5,
                                'description': "Only accessible on the skipper. You'll catch fish out here which you can't catch anywhere else. Who knows what you'll hook?"}
                  }

WEIGHT_CONVERSIONS = {'kg': 2.204623,
                      'lb': 1,
                      'pound': 1,
                      'oz': 0.0625,
                      'ounce': 0.0625}

ACTIVITIES = ('have a beer.',
              'resist the urge to check twitter.',
              'enjoy the view.',
              'take a load off.',
              'reflect on the good things in life.',
              'talk to the boys in the GroupMe.',
              'feel the vibes.',
              'relax to some music.')


CATCH_RESPONSES = {0: ["{} caught a {}lb {}! Nice!",
                       "{} hooked a {}lb {}! Nice going!",
"{} caught a {}lb {}! Way to go!"],
                   1: ["{} caught a {}lb {}! That's no small fry!",
                       "{} hooked a {}lb {}! That one's worth a picture!"],
                   2: ["Wow! {} caught a {}lb {}! That's one hell of a catch!",
                       "What a catch! {} caught a {}lb {}! Take a picture or your friends won't believe you!"],
                   3: ["Holy shit! What a catch! {} caught a {}lb {}! Now THAT'S a fish!"],
                   4: ["WHOA! {} caught a {}lb {}! Any bigger and you're gonna need a bigger boat!"]}

easter_eggs = ("While traveling back to shore, {0} thinks they hear singing over the side of the boat. When they peer over the side, they see what looks like several mermaids swimming a few feet below the surface. {0} makes eye contact with one of them. The creature smiles, revealing a row of razor-sharp teeth. Giggling, they swim out of sight.",
               "On their journey back to shore, {0} sees a massive dorsal fin over the starboard bow. It looks like a shark fin, but it's at least twice as big as the dorsal fin of a great white. Luckily, it's swimming away from the boat.",
               "While watching the horizon on their journey back to shore, {0} sees a massive creature rise out of the ocean far off in the distance. {0} must be dreaming; there are no known animals that grow to even a tenth of that size. The sky grows dark. The clouds swirl. A deafening sound sweeps over the ocean. Slowly, the creature sinks beneath the waves. The weather calms. No one ever believes {0}'s story; psychologically, they're never quite the same.",
               "On their journey back to shore, {0} passes a huge cargo ship headed in the opposite direction. Several minutes later, a flare is fired into the air. {0} turns around to see the cargo ship far off in the distance. It is sinking; it looks like it has been broken in half. Two giant tentacles have grabbed one of the halves of the ship. Within a minute, both halves of the ship disappear below the waves."
               )

def rebuildDB(reinsert=None):
    '''
    This rebuilds the entire fishing SQLite database.
    '''

    #------------------------------#
    #-- Create the fish database --#
    #------------------------------#

    # Load the fish data into memory as a dictionary
    with open('fishfacts.pickle', mode='rb') as f:
        fishfacts = pickle.load(f)

    conn = psycopg2.connect(DATABASE_URL, sslmode='require')

    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS Fish (
       ID INT UNIQUE GENERATED ALWAYS AS IDENTITY,
       Name TEXT NOT NULL UNIQUE,
       Size TEXT NOT NULL,
       Food_Value TEXT NOT NULL,
       Game_Quality TEXT NOT NULL
       )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS Habitats (
       Habitat TEXT NOT NULL,
       Fish_ID INTEGER NOT NULL,
       FOREIGN KEY (Fish_ID)
          REFERENCES Fish (ID),
       UNIQUE (Habitat, Fish_ID)
       )
    ''')

    c.execute('''
      CREATE TABLE IF NOT EXISTS Players (
        ID INT UNIQUE,
        Rod_level INT NOT NULL,
        Boat_level INT NOT NULL
    );
    ''')

    c.execute('''CREATE TABLE IF NOT EXISTS Catches (
      Catch_ID INT UNIQUE GENERATED ALWAYS AS IDENTITY,
      Player_ID INTEGER NOT NULL,
      Fish_ID INTEGER NOT NULL,
      Size INTEGER NOT NULL,
      FOREIGN KEY (Player_ID)
        REFERENCES Players (ID),
      FOREIGN KEY (Fish_ID)
        REFERENCES Fish (ID)
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS CurrentFishers (
      Player_ID INT UNIQUE,
      Resolve_time INT NOT NULL,
      Location TEXT NOT NULL,
      FOREIGN KEY (Player_ID)
        REFERENCES Players (ID)
      )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS Topics (
      topic TEXT UNIQUE,
      Christopher INT,
      Danny INT,
      Evan INT,
      Dylan INT,
      Lars INT,
      Cole INT,
      Diego INT,
      Taco INT,
      Marcus INT,
      Everyone INT
      )
    ''')

    if reinsert:
        # Insert the fish data into the tables
        for fishname, fishatts in fishfacts.items():
            # Ignore invalid data
            if len(fishatts) != 4 : continue
            if re.search('in|f|c|m|"', fishatts['Size']): continue

            # Insert the data
            c.execute('''INSERT INTO Fish (Name,
                         Size,
                         Food_Value,
                         Game_Quality) VALUES (%s, %s, %s, %s)''',
                      (fishname, fishatts['Size'],
                       fishatts['Food Value'],
                       fishatts['Game Qualities']))
            c.execute('''SELECT ID FROM Fish WHERE Name = %s''', (fishname,))
            id = c.fetchone()[0]
            habitats = fishatts['Habitats'].split(', ')
            for habitat in habitats:
                c.execute('''INSERT INTO Habitats
                                (Habitat, Fish_ID)
                            VALUES (%s, %s)''', (habitat, id))

    # Close the SQLite connection
    conn.commit()
    conn.close()


def calc_avg_habitat(habitat):
    '''
    Returns the average fish size for a given habitat.
    Used to generate the HABITATS_AVG_LB constant.
    '''

    # Get the sizes
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    c = conn.cursor()
    c.execute('''SELECT Size
                 FROM Fish
                 WHERE ID IN (
                   SELECT Fish_ID
                   FROM Habitats
                   WHERE Habitat = %s)''', (habitat,)
              )
    size_raw = [size[0] for size in c.fetchall()]
    # Extract the numbers
    size_list = [re.findall(r'[0-9.]+', entry)
                 for entry in size_raw]
    # Find the metric
    metric_regex = "|".join(WEIGHT_CONVERSIONS.keys())
    metrics = [re.search(metric_regex, string)[0]
               for string in size_raw]

    def compute_avg(nums, metric):
        if len(nums) > 2: nums = nums[:2]
        nums = [float(num) for num in nums]
        avg = stats.mean(nums)
        avg_normalized = avg * WEIGHT_CONVERSIONS[metric]
        return avg_normalized

    avgs = [compute_avg(entry, met)
            for entry, met in zip(size_list, metrics)]
    conn.commit()
    conn.close()
    return stats.mean(avgs)


def calc_habitat_catch_rate_modifier(habitat):
    '''
    Calculate the catch modifier for each habitat.
    Habitats with larger average catches are less likely to catch fish.

    Returns a percent value i.e. between 0 and 100, although it should never be
    lower than 75.
    '''
    return (0.75 + (0.25/(1 + math.exp(0.5*(HABITATS_AVG_LB[habitat]['size'] - 21))))) * 100


def calc_fish_difficulty(size):
    '''
    Calculate the difficulty of catching the fish as a function of its size.
    The value is the percentage of times a fisher should fail to catch the fish.
    i.e. it should be between 0 and 100.
    '''
    return (100/(1 + math.exp(0.12*(50-size))))


def goFishing(habitat, boat, boat_level, rod_level):
    '''
    Return a fish if one is caught, or nothing if one is not caught.
    Also check if something else goes wrong; if it does, return
    a string.
    '''

    # Check if they have access to their requested boat
    if BOAT_LEVELS[boat] > boat_level: return "You can't use this boat yet."
    # Check if their boat level is high enough for the habitat
    if boat_level < HABITATS_AVG_LB[habitat]['level']:
        return "Your boat isn't well suited to fishing in this location."

    #-------------------------#
    #-- Try to catch a fish --#
    #-------------------------#

    # Calculate how likely a catch is based on the habitat
    catchrate = calc_habitat_catch_rate_modifier(habitat)

    # Use the catchrate to randomly decide if a fish is caught.
    # If not, return nothing.
    if random.randint(0, 100) > catchrate: return None


    #----------------------------#
    #-- Generate a random fish --#
    #----------------------------#

    # A fish is caught; select a fish from the DB and
    # generate an appropriate size.
    with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
        c = conn.cursor()
        c.execute('''
          SELECT *
          FROM Fish
          WHERE ID IN
            (SELECT Fish_ID
            FROM Habitats
            WHERE Habitat = %s)
          ORDER BY random()
          LIMIT 1''',
                  (habitat,))
        fish = c.fetchone()

    # Generate the size ----------------------------------------------------
    # Extract the average size range
    size_list = [float(vals) for vals in
                 re.findall(r'[0-9.]+', fish[2])]
    # Truncate the list to only the first two values (if there are more than 1)
    if len(size_list) > 2: size_list = size_list[:2]
    # Find the average size
    avg_size = stats.mean(size_list)
    # Find the standard deviation
    sd = (max(size_list) - min(size_list))/4 if len(size_list) > 1 else size_list[0]/10
    # Generate a size from the normal distribution
    fish_size = max(random.gauss(avg_size, sd), 0.2)

    # Normalize the weight --------------------------------------------------
    # Find the metric
    metric_regex = "|".join(WEIGHT_CONVERSIONS.keys())
    metric = re.search(metric_regex, fish[2])[0]
    # Normalize the weight
    fish_size_normalized = round(fish_size * WEIGHT_CONVERSIONS[metric],
                                 2)


    #--------------------------------------#
    #-- Check if the catch is successful --#
    #--------------------------------------#

    difficulty = calc_fish_difficulty(fish_size_normalized)
    # Check if there was a problem with the rod
    if random.randint(0, 100) < difficulty - RODS[rod_level - 1][1]:
        return problem('rod')
    # Check if there was a problem with the boat
    elif random.randint(0, 100) < difficulty - BOATS[boat_level - 1][1]:
        return problem('boat')
    # If not, return a tuple containing info about the fish
    else:
        return (tuple(fish), fish_size_normalized)


def problem(prob_type):
    rod = ["{} hooked a fish but it was too strong for their fishing rod. They had to cut the line to keep it from snapping.",
           "{} caught something, but whatever it was, it was too strong; after a long fight, their line snapped and the fish escaped.",
           "{} hooked something, but it proved too strong for their fishing line. Their line snapped."]
    boat = ["{} was caught off guard by a large catch and was pulled overboard. How humbling.",
            "{} caught something big but their boat wasn't steady enough to reel it in. They cut the line to avoid capsizing."]
    if prob_type == "rod":
        return random.choice(rod)
    elif prob_type == "boat":
        return random.choice(boat)


def getInfo(topic="user", user_id=None):
    '''Return various strings when the user
    requests info.
    '''

    def stringify_info(obj):
        '''Format the string for rods and boat info.
        '''

        return "\n\n".join([": ".join(["Tier "
                                       + str(num + 1)
                                       + ", "
                                       + entry[0].title(), entry[2]])
                            for num, entry in enumerate(obj)])

    def format_habs():
        '''Format the sting for habitat info.
        '''

        sorted_locations = sorted(HABITATS_SET,
                                  key=lambda x: HABITATS_AVG_LB[x]['level'])
        return "\n".join(["{}: requires the {}"\
                          .format(name,
                                  BOATS[HABITATS_AVG_LB[name]['level'] - 1][0])
                          for name in sorted_locations])

    async def inner_wrapper(topic="leaderboard", user_id=user_id):
        '''This lets us call the groupme api and get the sql
        calls concurrently.
        '''

        # Schedule getting the users
        get_users_task = asyncio.create_task(get_users_from_api())

        # Get the leaderboard data
        with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
            c = conn.cursor()

            # Biggest Fish
            c.execute('''
            SELECT Player_ID,
                   c.Name,
                   Catches.size
            FROM Catches
            INNER JOIN Fish c
              ON Catches.Fish_ID = c.ID
            ORDER BY Catches.size DESC
            LIMIT 5
            ''')
            biggest_fish = c.fetchall()

            # Most pounds of fish
            c.execute('''
            SELECT Player_ID,
                   sum(size) AS pounds
            FROM Catches
            GROUP BY Player_ID
            ORDER BY pounds DESC
            LIMIT 5
            ''')
            most_pounds = c.fetchall()

            # Most different kinds of fish
            c.execute('''
            SELECT Player_ID,
                   count(Fish_ID) AS Species
            FROM (
              SELECT DISTINCT Player_ID,
                              Fish_Id
              FROM Catches
            ) AS distinct_catches
            GROUP BY Player_ID
            ORDER BY Species DESC
            LIMIT 5
            ''')
            different_fish = c.fetchall()

        await get_users_task

        # Get the user nicknames
        users = get_users_task.result()
        gm_users = {entry['user_id']: entry['nickname']
                    for entry in users}

        # Join the data
        biggest_fish_joined = [(gm_users[str(entry[0])], entry[1], entry[2])
                               for entry in biggest_fish if str(entry[0])
                               in gm_users.keys()]
        most_pounds_joined = [(gm_users[str(entry[0])], entry[1])
                               for entry in most_pounds if str(entry[0])
                               in gm_users.keys()]
        different_fish_joined = [(gm_users[str(entry[0])], entry[1])
                                 for entry in different_fish if str(entry[0])
                                 in gm_users.keys()]

        # Make the data into readable strings
        bf_string = "Biggest fish caught\n----------------------\n"\
                    + "\n".join(["{}. {}, {}, {}lbs"\
                                   .format(num + 1, entry[0],
                                           entry[1], entry[2])
                                   for num, entry
                                   in enumerate(biggest_fish_joined)])

        mp_string = "Most lbs of fish\n-------------------------\n"\
                    + "\n".join(["{}. {}, {} total lbs"\
                                   .format(num + 1, entry[0], entry[1])
                                   for num, entry
                                   in enumerate(most_pounds_joined)])

        df_string = "Most species of fish caught\n-------------------------\n"\
                    + "\n".join(["{}. {}, {} total species"\
                                   .format(num + 1, entry[0], entry[1])
                                   for num, entry
                                   in enumerate(different_fish_joined)])
        return "\n\n".join([bf_string, mp_string, df_string])

    if topic =="user":
        # Return user stats
        data = getUser(user_id)
        user_catches = getUserCatches(user_id)
        return "Boat level: {}\nRod level: {}\n".format(data[2], data[1])\
               + "Total number of fish caught: {}\nNumber of species caught: {}/169\nTotal lbs of fish caught: {}\n\n"\
                   .format(len(user_catches), countUniqueCatches(user_id), sumTotalPoundsCaught(user_id))\
               + "Largest fish caught:\n"\
               + "\n".join(["{}. {}, {}lbs".format(num + 1, entry[0], entry[1])
                            for num, entry
                            in enumerate(user_catches[:min(
                                5,
                                len(user_catches)
                            )])])\

    elif topic == 'lstats':
        return "Catches by habitat:\n"\
               + countCatchesByHabitat(user_id)
    # Display leaderboard data
    elif topic == "leaderboard":
        return asyncio.run(inner_wrapper())
    # Display boat data
    elif topic.lower() == "boats":
        return stringify_info(BOATS)
    # Display rod data
    elif topic.lower() == "rods":
        return stringify_info(RODS)
    # Display aggregate habitat info
    elif topic.lower() == "habs":
        return format_habs()
    # Display habitat information
    elif topic.title() in HABITATS_AVG_LB.keys():
        return HABITATS_AVG_LB[topic.title()]['description']


async def get_users_from_api():
    '''This fetches users from the groupme API.

    It is an async function, so we can schedule a task in our wrapper
    function and await the results while doing other, non I/O bound
    things.
    '''

    r = requests.get('https://api.groupme.com/v3/groups/16489941',
                     params = {'token': os.environ['token']})\
                .json()['response']['members']

    return r


def getUser(user_id):
    '''Get a user's values from the database.
    '''

    with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
        c = conn.cursor()
        c.execute("SELECT ID FROM Players")
        users = [id[0] for id in c.fetchall()]
        if user_id not in users:
            c.execute("INSERT INTO Players VALUES (%s, 1, 1) ON CONFLICT DO NOTHING", (user_id,))
            conn.commit()
        c.execute("SELECT * FROM Players WHERE ID = %s", (user_id,))
        player_data = c.fetchone()
    return tuple(player_data)


def pickViableHabitat(level):
    '''Pick a viable habitat when supplied with a user's
    boat level.
    '''

    options = [entry[0] for entry in HABITATS_AVG_LB.items()
               if entry[1]['level'] <= level]
    return random.choice(options)


def fetchCurrentFishers():
    '''Get a list of the player ID for people who are
    currently fishing. Returns a list.
    '''

    with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
        c = conn.cursor()
        c.execute('''
          SELECT Player_ID
          FROM CurrentFishers
        ''')
        fishers = [entry[0] for entry in c.fetchall()]
    return fishers


def addCurrentFisher(user, location, rod_level):
    delay = max(0, int(random.gauss(60 - (3 * rod_level),
                                    20)) * 60)
    end_time = time.time() + delay
    with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
        c = conn.cursor()

        c.execute('''
          INSERT
          INTO CurrentFishers
          VALUES (%s, %s, %s)
          ON CONFLICT DO NOTHING
        ''', (user,
              end_time,
              location))

        conn.commit()

    return abs(delay)


def resolveFisher(fish_catch, user_id, habitat, delay, boat_level, rod_level):
    '''
    The process which runs when someone starts fishing.
    This runs on its own process, so Flask can return a value
    and end the connection while still sending a reply much later.
    Hopefully, this will avoid timeouts.
    '''

    async def inner_wrapper(fish_catch=fish_catch,
                            user_id=user_id,
                            habitat=habitat,
                            delay=delay):
        '''This lets us await get_users_from_api while still running
        resolveFisher as an independent process. In practice,
        this contains almost all of the code which is run
        when resolveFisher is called.
        '''

        #------------------------------------------#
        #-- Fetch nicknames from the Groupme API --#
        #------------------------------------------#

        # Start an asyncio task to get the users from the API
        groupme_users = asyncio.create_task(get_users_from_api())
        user_nickname = False

        #--------------------------------#
        #-- Random Encounters Behavior --#
        #--------------------------------#

        # There's a 1 in 3 chance of meeting another fisher
        if random.randint(1, 3) == 1:
            # Get the other fishers who are in the same location
            with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
                c = conn.cursor()
                c.execute('''
                  SELECT Player_ID, Resolve_time
                  FROM CurrentFishers
                  WHERE Location =%s
                ''', (habitat,))
                # Exclude the current fisher from the list
                results = [result
                           for result in c.fetchall()
                           if result[0] != user_id]

            # If there are other fishers:
            if results:
                # Pick a random one
                fisher = random.choice(results)
                # Pick a random amount of time to delay. Make sure
                # it's an integer, less than the amount of time
                # before either fisher resolves, and more than
                # zero.
                interact_delay = random\
                    .randint(0, max(int(min(fisher[1] - time.time(),
                                            delay)),
                                    0))

                # Wait the specified amount of time
                await asyncio.sleep(interact_delay)

                # Get the group members
                await groupme_users
                # Extract the result from the asyncio.Task object
                groupme_users_result = groupme_users.result()
                fisher_fname = [user for user in groupme_users_result
                                 if user['user_id'] ==\
                                 str(user_id)][0]['name'].split()[0]
                # Find the user's nickname
                user_nickname = [user for user in groupme_users_result
                                 if user['user_id'] ==\
                                 str(user_id)][0]['nickname']
                # Find the selected other fisher's nickname
                other_nickname = [user for user in groupme_users_result
                                  if user['user_id'] ==\
                                  str(fisher[0])][0]['nickname']

                # Get the fisher's first name to index their topics
                with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
                    c = conn.cursor()
                    try:
                        c.execute(f'''
                          SELECT topic
                          FROM Topics
                          WHERE {fisher_fname} = 1
                        ''')
                    except:
                        c.execute('''
                          SELECT topic
                          FROM Topics
                          WHERE Everyone = 1
                        ''')
                    topic = random.choice([entry[0] for
                                           entry in c.fetchall()])

                # Select a random adjective
                adj = random.choice(TOPIC_ADJ)

                # Send a message about the conversation they have
                message = f"{user_nickname} encounters {other_nickname} out on the waters. They have a {adj} conversation about {topic}."

                # Specify what message to send
                data = {'bot_id': os.environ['bot_id'],
                        'text': message}

                # Send the post request to the group
                if checkStillFishing(user_id):
                    r = requests.post('https://api.groupme.com/v3/bots/post',
                                      data=data)

                # Update the waiting time
                delay -= interact_delay

        #------------------------------------------#
        #-- Respond to the fishing request after --#
        #-- some time has passed ------------------#
        #------------------------------------------#

        # Wait a specified amount of time
        await asyncio.sleep(max(delay, 0))
        # Wait until the request completes, then get a list of the users
        await groupme_users
        # Extract the fisher's nickname
        if not user_nickname:
            groupme_users_result = groupme_users.result()
            user_nickname = [user for user in groupme_users_result
                             if user['user_id'] ==\
                             str(user_id)][0]['nickname']

        # Check to make sure resetFishingStatus
        # hasn't been called manually.
        if checkStillFishing(user_id):

            # Remove the user from the table of current fishers
            resetFishingStatus(user_id)

            # Send a message if they failed to catch a fish ------------
            if not fish_catch:
                no_catch_messages = ['{} thought they caught a fish, but when they reeled in their line all they found was seaweed.',
                                     '{} reeled in their line, but instead of a fish, they found they\'d only hooked an old tire.',
                                     '{} reeled in their line to find that something had stolen their bait.',
                                     'Due to worries about an approaching storm, {} reeled in their line and returned to shore.']
                text_value = random.choice(no_catch_messages)\
                                .format(user_nickname)

            # If fish_catch is a string, the fisher had a problem
            # with their boat or rod. Format and relay that message.
            elif type(fish_catch) == str:
                text_value = fish_catch.format(user_nickname)

            # Otherwise, they caught a fish!
            elif type(fish_catch) == tuple:
                # Save the fish in the catches database table
                registerCatch(user_id=user_id,
                              fish=fish_catch)

                # Construct a catch message
                size_picker = min(int(fish_catch[1]/30), 4)
                text_value = random.choice(CATCH_RESPONSES[size_picker])\
                                   .format(user_nickname, fish_catch[1], fish_catch[0][1])\
                             + f"\nFood Value: {fish_catch[0][3]}\nGame Quality: {fish_catch[0][4]}"


            # Send the post request to the group
            data = {'bot_id': os.environ['bot_id'],
                    'text': text_value}
            r = requests.post('https://api.groupme.com/v3/bots/post', data=data)
            await asyncio.sleep(2)



            # Easter eggs
            if habitat.lower() in ("offshore", "inshore", "reef") and random.randint(0, 1000) == 500:
                e_egg = random.choice(easter_eggs)
                data = {'bot_id': os.environ['bot_id'],
                        'text': e_egg.format(user_nickname)}
                r = requests.post('https://api.groupme.com/v3/bots/post', data=data)
                await asyncio.sleep(2)



            # Check for level ups and add messages
            if boat_level < 5 and sumTotalPoundsCaught(user_id) > LEVEL_CHECKS['boat'][boat_level-1][1]:
                incrementLevel(user_id, "Boat_level")
                # Send the message notifying the levelup
                data = {'bot_id': os.environ['bot_id'],
                        'text': LEVEL_CHECKS['boat'][boat_level - 1][2]\
                            .format(user_nickname)}
                r = requests.post('https://api.groupme.com/v3/bots/post', data=data)

            if rod_level < 5 and countUniqueCatches(user_id) >= LEVEL_CHECKS['rod'][rod_level-1][1]:
                incrementLevel(user_id, "Rod_level")
                # Send the message notifying the levelup
                data = {'bot_id': os.environ['bot_id'],
                        'text': LEVEL_CHECKS['rod'][rod_level - 1][2]\
                            .format(user_nickname)}
                r = requests.post('https://api.groupme.com/v3/bots/post', data=data)


    #----------------------------#
    #-- Run the inner function --#
    #----------------------------#

    # Run the inner function as an asyncio coroutine
    # (this is necessary to make the requests asynchronous)
    asyncio.run(inner_wrapper())


def incrementLevel(user_id, level_type):
    with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
        sqlquery = f'''
          UPDATE Players
          SET {level_type} = {level_type}  + 1
          WHERE ID =%s
        '''
        c = conn.cursor()
        c.execute(sqlquery, (user_id,))

        conn.commit()


def resetFishingStatus(user_id):
    '''
    Manually remove a fisher from the table of current
    fishers.
    '''

    with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
        c = conn.cursor()
        c.execute('''
          DELETE
          FROM CurrentFishers
          WHERE Player_ID = %s
        ''', (user_id,))
        conn.commit()


def checkStillFishing(user_id):
    '''
    Check whether the fishing was interrupted.

    Returns a bool
    '''

    user_id = int(user_id)
    with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
        c = conn.cursor()
        c.execute('''
          SELECT Player_ID
          FROM CurrentFishers
          WHERE Player_ID = %s
        ''', (user_id,))
        fishers = c.fetchall()

    response = (user_id,) in fishers
    return response


def getUserCatches(user_id):
    with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
        c = conn.cursor()
        c.execute('''
          SELECT b.Name,
                 a.size
          FROM (
            SELECT size, Fish_ID
            FROM Catches
            WHERE Player_ID =%s
          ) a
          LEFT JOIN Fish b
            ON a.Fish_ID=b.ID
          ORDER BY a.size DESC
        ''', (user_id,))
        catches = c.fetchall()

    return catches


def countUniqueCatches(user_id):
    catches = getUserCatches(user_id)
    set_catches = {catch[0]
                   for catch in catches}

    return len(set_catches)


def sumTotalPoundsCaught(user_id):
    catches = getUserCatches(user_id)
    return sum([catch[1] for catch
                in catches])


def registerCatch(user_id, fish):
    '''
    Log a caught fish in the SQLite Catches
    table.

    The `fish` argument should be a fish
    generated by goFishing().
    '''

    with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
        c = conn.cursor()
        c.execute('''
          INSERT
          INTO Catches
          (Player_ID, Fish_ID, Size)
          VALUES (%s, %s, %s)
        ''', (user_id,
              fish[0][0],
              fish[1]))

        conn.commit()


def countCatchesByHabitat(user_id):
    '''Returns a descriptive string.
    '''

    # Get the counts from the database
    with psycopg2.connect(DATABASE_URL, sslmode='require') as conn:
        c = conn.cursor()
        c.execute('''
          SELECT a.Habitat,
                 b.counts,
                 a.hab_counts
          FROM (
            SELECT Habitat,
                   count(Fish_Id) AS hab_counts
            FROM Habitats
            GROUP BY Habitat
          ) a
          LEFT JOIN (
            SELECT Habitat,
                   count(Habitat) AS counts
            FROM Habitats
            WHERE Fish_ID IN (
              SELECT DISTINCT Fish_ID
              FROM Catches
              WHERE Player_ID = %s)
            GROUP BY Habitat) b ON a.Habitat = b.Habitat
        ''', (user_id,))
        counts = c.fetchall()

    # Create a dictionary
    counts_dict = {entry[0]: {'caught': entry[1],
                              'total': entry[2]}
                   for entry in counts}

    # Replace elements which are 'None' with 0
    for element in counts_dict:
	    if counts_dict[element]['caught'] is None:
		    counts_dict[element]['caught'] = 0

    # Format a text string with the dictionary
    count_text = "\n".join(["{}: {} out of {} species caught."\
                              .format(entry,
                                      counts_dict[entry]['caught'],
                                      counts_dict[entry]['total'])
                              for entry in counts_dict])
    # Return the string
    return count_text


if __name__ == "__main__":
    rebuildDB()
