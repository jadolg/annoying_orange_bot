import os
import sched

import time
import uuid
from threading import Thread

from RocketChatBot import RocketChatBot
from future.backports import datetime
from pymongo import MongoClient

from dateparser import parse_next_event_from_string, is_event_recurring
from str_util import get_users_str, get_when

bot_name = os.environ['BOTNAME']
bot_password = os.environ['BOTPASSWORD']
server_url = os.environ['SERVERURL']
db_host = os.environ['DBHOST']
db_port = int(os.environ['DBPORT'])

event_list = []

SCHEDULER_EVENTS_PRIORITY = 1

bot = RocketChatBot(bot_name, bot_password, server_url)

db_client = MongoClient(db_host, db_port)
reminders = db_client['events'].reminders

error_msg = f'''
I don't understand what you want me to do :(. You can ask me to remind you things using the following syntax:\n
@{bot_name} remind @user and @user2 *to* commit changes on their projects *at/in/every* day at 5 pm
'''


def add_reminder(msg, user, channel_id):
    try:
        [who, what] = str(msg).split('to ', 1)
        schedule_event(who, what, user, channel_id)
    except Exception as e:
        print(e)
        bot.send_message(error_msg, channel_id)


def post_reminder(who, what, user, channel_id, event_id):
    users = get_users_str(who=who, user=user)
    what_without_when = str(what).replace(get_when(what), '')
    bot.send_message(f'{" ".join(users)}, {user} wants you to remember to {what_without_when}', channel_id)

    for event in event_list:
        if str(event_id) == str(event['id']):
            event_list.remove(event)

    if is_event_recurring(what):
        schedule_event(who, what, user, channel_id, event_id=event_id, from_db=True)
    else:
        reminders.delete_one({'event_id': event_id})


def get_reminders(msg, user, channel_id):
    if not event_list:
        bot.send_message('There are no scheduled events', channel_id)
        return
    result = ''
    for event in event_list:
        time_for_next_event = parse_next_event_from_string(event['msg'])
        result += f" - *{event['id']}* " \
                  f"remind *{event['who']}* " \
                  f"to {event['msg']} " \
                  f"[next execution: *{datetime.datetime.fromtimestamp(time_for_next_event)}*] " \
                  f"added by *{event['user']}*\n"

    bot.send_message(result, channel_id)


def delete_reminder(msg, user, channel_id):
    for event in event_list:
        if str(msg).strip() == str(event['id']):
            event['scheduler'].cancel(event['event'])
            event_list.remove(event)
            reminders.delete_one({'event_id': event['id']})
            bot.send_message(f"Deleted event {event['id']}", channel_id)
            return

    bot.send_message(f"Can't find event {event['id']}", channel_id)


def schedule_event(who, what, user, channel_id, event_id=None, from_db=False):
    scheduler = sched.scheduler(time.time, time.sleep)
    if not event_id:
        event_id = uuid.uuid4()
    time_for_next_event = parse_next_event_from_string(what)
    event = scheduler.enterabs(time_for_next_event, SCHEDULER_EVENTS_PRIORITY, post_reminder,
                               argument=(who, what, user, channel_id, event_id))
    event_list.append(
        {
            'id': event_id,
            'msg': what,
            'who': who,
            'user': user,
            'event': event,
            'scheduler': scheduler
        }
    )

    if who.strip() != 'me':
        person = who
    else:
        person = f'@{user}'

    if not from_db:
        reminders.insert_one(
            {
                'who': who,
                'what': what,
                'user': user,
                'channel_id': channel_id,
                'event_id': event_id,
            }
        )

        bot.send_message(
            f"I'll remind {person} to {what} at "
            f"*{datetime.datetime.fromtimestamp(time_for_next_event)}*. "
            f"Event _id_ is *{event_id}*",
            channel_id
        )

    scheduler.run()


def get_help(msg, user, channel_id):
    help_str = f"""
    Hi @{user} I'm @{bot_name} and I was built to remind you of important things.
    Here is how you can use me (by example because my maker is lazy as hell):
    - @{bot_name} remind @{user} *to* buy milk *on* Wednesdays at 4 pm
    - @{bot_name} remind @{user} *to* drink water *every* 20 minutes
    - @{bot_name} remind me *to* check my food *in* the microwave in 5 minutes
    - @{bot_name} remind @{user} *to* get ready for TGIF on Fridays at 1 pm
    
    Want to know how many reminders I have scheduled?
    - @{bot_name} list
    
    Want to finally cancel that annoying reminder?
    - @{bot_name} cancel _id_
    where _id_ is the id of the event you get when running `@{bot_name} list` 
    """

    bot.send_message(help_str, channel_id)


bot.add_dm_handler(['remind', ], add_reminder)
bot.add_dm_handler(['list', 'events', 'reminders', 'get reminders', ], get_reminders)
bot.add_dm_handler(['delete', 'remove', 'cancel'], delete_reminder)
bot.add_dm_handler(['help', ], get_help)
bot.unknow_command = [error_msg, ]

reminders_cursor = reminders.find({})
for reminder in reminders_cursor:
    Thread(target=schedule_event, args=(reminder['who'],
                                        reminder['what'],
                                        reminder['user'],
                                        reminder['channel_id'],
                                        reminder['event_id'],
                                        True
                                        )).start()

print('starting bot...')
bot.run()
