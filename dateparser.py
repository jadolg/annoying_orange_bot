import datetime
import time
from dateutil import rrule
from parsedatetime import parsedatetime
from recurrent import RecurringEvent


def parse_next_event_from_string(s):
    r = RecurringEvent(now_date=datetime.datetime.now())
    r.parse(s)
    if r.is_recurring:
        rr = rrule.rrulestr(r.get_RFC_rrule())
        return time.mktime(rr.after(datetime.datetime.now()).timetuple())
    else:
        cal = parsedatetime.Calendar()
        if time.mktime(datetime.datetime.now().timetuple()) == time.mktime(cal.parse(s)[0]):
            raise Exception("Can't understand this time expression")
        return time.mktime(cal.parse(s)[0])


def is_event_recurring(s):
    r = RecurringEvent(now_date=datetime.datetime.now())
    r.parse(s)
    return r.is_recurring
