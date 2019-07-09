import os
import sched
import time
import uuid
from threading import Thread

from aiohttp import web
from future.backports import datetime
from pymongo import MongoClient
from rocketchat_API.rocketchat import RocketChat

from dateparser import parse_next_event_from_string, is_event_recurring
from str_util import get_users_str, get_when

bot_name = os.environ['BOTNAME']
bot_password = os.environ['BOTPASSWORD']
server_url = os.environ['SERVERURL']
db_host = os.environ['DBHOST']
db_port = int(os.environ['DBPORT'])

event_list = []

SCHEDULER_EVENTS_PRIORITY = 1

rocket = RocketChat(user=bot_name, password=bot_password, server_url=server_url)

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
        rocket.chat_post_message(error_msg, channel_id)


def post_reminder(who, what, user, channel_id, event_id):
    users = get_users_str(who=who, user=user)
    what_without_when = str(what).replace(get_when(what), '')
    if not users:
        rocket.chat_post_message(f'{user} wants you @all to remember to {what_without_when}', channel_id)
    else:
        rocket.chat_post_message(f'{" ".join(users)}, {user} wants you to remember to {what_without_when}', channel_id)

    for event in event_list:
        if str(event_id) == str(event['id']):
            event_list.remove(event)

    if is_event_recurring(what):
        schedule_event(who, what, user, channel_id, event_id=event_id, from_db=True)
    else:
        reminders.delete_one({'event_id': event_id})


def get_reminders(msg, user, channel_id):
    events = event_list
    if 'all' not in msg:
        events = [event for event in event_list if event['user'] == user]

    if not events:
        rocket.chat_post_message('There are no scheduled events', channel_id)
        return
    result = ''
    for event in events:
        time_for_next_event = parse_next_event_from_string(event['msg'])
        result += f" - *{event['id']}* " \
            f"remind {event['who']} " \
            f"to {event['msg']} " \
            f"[next execution: *{datetime.datetime.fromtimestamp(time_for_next_event)}*] " \
            f"added by *{event['user']}*\n"

    rocket.chat_post_message(result, channel_id)


def delete_reminder(msg, user, channel_id):
    for event in event_list:
        if str(event['id']) in msg:
            event['scheduler'].cancel(event['event'])
            event_list.remove(event)
            reminders.delete_one({'event_id': event['id']})
            rocket.chat_post_message(f"Deleted event {event['id']}", channel_id)
            return

    rocket.chat_post_message(f"Can't find event", channel_id)


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

        rocket.chat_post_message(
            f"I'll remind {person} to {what} at "
            f"*{datetime.datetime.fromtimestamp(time_for_next_event)}*. "
            f"Event _id_ is *{event_id}*",
            channel_id
        )

    Thread(target=scheduler.run).start()


def get_help(msg, user, channel_id):
    help_str = f"""
    Hi @{user} I'm @{bot_name} and I was built to remind you of important things.
    Here is how you can use me (by example because my maker is lazy as hell):
    - @{bot_name} remind @{user} to buy milk on Wednesdays at 4 pm
    - @{bot_name} remind @{user} to drink water every 20 minutes
    - @{bot_name} remind me to check my food in the microwave in 5 minutes
    - @{bot_name} remind @{user} to get ready for TGIF on Fridays at 1 pm
    
    Want to list the reminders I have scheduled?
    - @{bot_name} list
    
    Want to list all reminders?
    - @{bot_name} list all
    
    Want to finally cancel that annoying reminder?
    - @{bot_name} cancel _id_
    where _id_ is the id of the event you get when running `@{bot_name} list` 
    """

    rocket.chat_post_message(help_str, channel_id)


reminders_cursor = reminders.find({})
for reminder in reminders_cursor:
    Thread(target=schedule_event, args=(reminder['who'],
                                        reminder['what'],
                                        reminder['user'],
                                        reminder['channel_id'],
                                        reminder['event_id'],
                                        True
                                        )).start()


async def handle_message(request):
    post = await request.json()
    msg = post.get('text')
    if msg.startswith('@annoyingorange') and post.get('user_name') != 'annoyingorange':
        msg = msg.lstrip('@annoyingorange').strip()
        if msg.startswith('remind'):
            add_reminder(post.get('text'), post.get('user_name'), post.get('channel_id'))
        elif msg.startswith('events') or msg.startswith('events') or msg.startswith('list') or msg.startswith(
                'reminders'):
            get_reminders(post.get('text'), post.get('user_name'), post.get('channel_id'))
        elif msg.startswith('delete') or msg.startswith('remove') or msg.startswith('cancel'):
            delete_reminder(post.get('text'), post.get('user_name'), post.get('channel_id'))
        elif msg.startswith('help'):
            get_help(post.get('text'), post.get('user_name'), post.get('channel_id'))
        else:
            rocket.chat_post_message('wait what?', post.get('channel_id'))
        print(post)
    return web.Response(text='ok')


async def handle_healthcheck(request):
    return web.Response(text='alive')


app = web.Application()
app.add_routes([web.post('/hook', handle_message)])
app.add_routes([web.get('/healthcheck', handle_healthcheck)])

web.run_app(app, host='0.0.0.0', port=5000)
