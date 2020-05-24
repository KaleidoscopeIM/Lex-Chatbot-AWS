"""
This sample demonstrates an implementation of the Lex Code Hook Interface
in order to serve a sample bot which manages bookings for movie tickets.
Bot, Intent, and Slot models which are compatible with this sample can be found in the Lex Console
as part of the 'BookMovie' template.

For instructions on how to set up and test a bot, as well as additional samples,
visit the Lex Getting Started documentation http://docs.aws.amazon.com/lex/latest/dg/getting-started.html.
"""

import json
import datetime
import time
import os
import dateutil.parser
import logging
import re
import boto3
from config import *

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# --- Helpers that build all of the responses ---


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def confirm_intent(session_attributes, intent_name, slots, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


# --- Helper Functions ---


def safe_int(n):
    """
    Safely convert n value to int.
    """
    if n is not None:
        return int(n)
    return n


def try_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """

    try:
        return func()
    except KeyError:
        return None
        
def print_l(s):
    print("_______________________________")
    print(str(s))
    print("_______________________________")

client = boto3.client(
    "sns",
    aws_access_key_id= get_id(),
    aws_secret_access_key=get_access_key(),
    region_name=get_region()
    )

def send_sns(movie_name, theater_name,movie_date, movie_time,ticket_count,mobile):
    print_l("sending inside send sns yes")
    msg = 'Your booking is confirmed.\n' \
    'Summary of tickets:\n'\
    'Movie: ' + movie_name +' ' \
    '\nTheater:' + theater_name +' ' \
    '\nDate: ' + str(movie_date) + ' '+str(movie_time) +' ' \
    '\nTotal ticket: ' + str(ticket_count) +' ' \
    '\n\nThank you for booking with chatbot. '
    mobile_str = str(mobile)
    if not mobile_str.startswith('+1'):
        mobile_str = '+1'+mobile_str 
    print_l(mobile_str)
    print_l(msg)
    client.publish(
    PhoneNumber=mobile_str,
    Message=msg
    )
    
    
def isvalid_movie(movie):
    valid_movies = ['Thor: Love and Thunder','Black Panther 2','Captain Marvel 2','Doctor Strange in the Multiverse of Madness']
    return [aMovie for aMovie in valid_movies if movie.lower() in aMovie.lower()]
    
def isvalid_theater(theater_name):
    valid_theater = ['AMC Highwoods 20','Studio Movie Grill','AMC Veterans 24','Cobb Grove 16']
    return [aTheater for aTheater in valid_theater if theater_name.lower() in aTheater.lower()]

def isvalid_mobile(mobile):
    rule = re.compile(r'(^[+0-9]{1,3})*([0-9]{10,11}$)')
    return True if rule.search(mobile) else False
    
    
def isvalid_room_type(room_type):
    room_types = ['queen', 'king', 'deluxe']
    return room_type.lower() in room_types


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def get_day_difference(later_date, earlier_date):
    later_datetime = dateutil.parser.parse(later_date).date()
    earlier_datetime = dateutil.parser.parse(earlier_date).date()
    return abs(later_datetime - earlier_datetime).days


def add_days(date, number_of_days):
    new_date = dateutil.parser.parse(date).date()
    new_date += datetime.timedelta(days=number_of_days)
    return new_date.strftime('%Y-%m-%d')


def build_validation_result(isvalid, violated_slot, message_content):
    return {
        'isValid': isvalid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }

def validate_movie(slots):
    movie_name = try_ex(lambda: slots['MovieName'])
    theater_name = try_ex(lambda: slots['TheaterName'])
    movie_time = try_ex(lambda: slots['MovieTime'])
    movie_date = try_ex(lambda: slots['MovieDate'])
    ticket_count = safe_int(try_ex(lambda: slots['TicketCount']))
    mobile = try_ex(lambda: slots['Mobile'])

    if movie_name and not isvalid_movie(movie_name):
        return build_validation_result(
            False,
            'MovieName',
            'Showtime for the {} is not available. You can choose from currently available movies.'.format(movie_name)
        )
        
    if theater_name and not isvalid_theater(theater_name):
        return build_validation_result(
            False,
            'TheaterName',
            'Showtime in theater {} is not available. You can choose one from the list above.'.format(theater_name)
        )

    if movie_date:
        if not isvalid_date(movie_date):
            return build_validation_result(False, 'MovieDate', 'I did not understand date.  When would you like to watch your movie?')
        if datetime.datetime.strptime(movie_date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'MovieDate', 'Booking must be scheduled at least one day in advance.  Can you try a different date?')
        if datetime.datetime.strptime(movie_date, '%Y-%m-%d').date() >= datetime.date.today()+datetime.timedelta(days=30):
            return build_validation_result(False, 'MovieDate', 'I can book only upto 1 month in advance. Can you try a date between {} and {}?'.format(datetime.date.today(),datetime.date.today()+datetime.timedelta(days=30)))

    if ticket_count is not None and ticket_count < 1:
        return build_validation_result(
            False,
            'TicketCount',
            'You should book atleat one ticket. How many tickets would you like to book?'
        )
    if ticket_count is not None and ticket_count > 10:
        return build_validation_result(
            False,
            'TicketCount',
            'You can book upto 10 tickets using the chatbot. How many tickets would you like to book?'
        )
        
    if mobile is not None and not isvalid_mobile(mobile):
        return build_validation_result(
            False,
            'Mobile',
            '{} is not a valid mobile number. Please provide a valid mobile number?'.format(mobile)
        )

    return {'isValid': True}


""" --- Functions that control the bot's behavior --- """


def book_movie(intent_request):
    """
    Performs dialog management and fulfillment for booking a movie.

    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """
    print_l(intent_request)
    
    movie_name = try_ex(lambda: intent_request['currentIntent']['slots']['MovieName'])
    theater_name = try_ex(lambda: intent_request['currentIntent']['slots']['TheaterName'])
    movie_date = try_ex(lambda: intent_request['currentIntent']['slots']['MovieDate'])
    movie_time = try_ex(lambda: intent_request['currentIntent']['slots']['MovieTime'])
    ticket_count = safe_int(try_ex(lambda: intent_request['currentIntent']['slots']['TicketCount']))
    mobile = try_ex(lambda: intent_request['currentIntent']['slots']['Mobile'])
    confirmation_status = intent_request['currentIntent']['confirmationStatus']
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    # Load confirmation history and track the current reservation.
    reservation = json.dumps({
        'ReservationType': 'Movie',
        'MovieName': movie_name,
        'TheaterName': theater_name,
        'MovieDate': movie_date,
        'MovieTime': movie_time,
        'TicketCount': ticket_count,
        'Nights': mobile
    })

    session_attributes['currentReservation'] = reservation

    if intent_request['invocationSource'] == 'DialogCodeHook':
        # Validate any slots which have been specified.  If any are invalid, re-elicit for their value
        validation_result = validate_movie(intent_request['currentIntent']['slots'])
        if not validation_result['isValid']:
            slots = intent_request['currentIntent']['slots']
            slots[validation_result['violatedSlot']] = None

            return elicit_slot(
                session_attributes,
                intent_request['currentIntent']['name'],
                slots,
                validation_result['violatedSlot'],
                validation_result['message']
            )
        if confirmation_status == 'Confirmed':
            sns = send_sns(movie_name, theater_name,movie_date, movie_time,ticket_count,mobile)
            return delegate(session_attributes, intent_request['currentIntent']['slots'])
        # Otherwise, let native DM rules determine how to elicit for slots and prompt for confirmation.  Pass price
        # back in sessionAttributes once it can be calculated; otherwise clear any setting from sessionAttributes.

        session_attributes['currentReservation'] = reservation
        return delegate(session_attributes, intent_request['currentIntent']['slots'])

    # Booking the Movie.  In a real application, this would likely involve a call to a backend service.
    logger.debug('BookMovie under={}'.format(reservation))

    # try_ex(lambda: session_attributes.pop('currentReservationPrice'))
    try_ex(lambda: session_attributes.pop('currentReservation'))
    session_attributes['lastConfirmedReservation'] = reservation

    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'Thank you! Your booking is confirmed.'
                     
        }
    )


# --- Intents ---


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']
    # Dispatch to your bot's intent handlers
    if intent_name == 'BookMovie':
        return book_movie(intent_request)


    raise Exception('Intent with name ' + intent_name + ' not supporte etesffd')


# --- Main handler ---


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    return dispatch(event)
