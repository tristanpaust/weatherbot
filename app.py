import os
import time
import json
import datetime
from slackclient import SlackClient
import pyowm
import nltk
from nltk import word_tokenize, pos_tag, ne_chunk

BOT_NAME = 'weatherbot'

SLACK_BOT_TOKEN = 'SLACK TOKEN'  # got off of slack page
owm = pyowm.OWM('Open Weather Map Token') # available after creating account at https://home.openweathermap.org

slack_client = SlackClient(SLACK_BOT_TOKEN)

api_call = slack_client.api_call("users.list")
if api_call.get('ok'):
    # retrieve all users so we can find our bot
    users = api_call.get('members')
    for user in users:
        if 'name' in user and user.get('name') == BOT_NAME:
            print("Bot ID for '" + user['name'] + "' is " + user.get('id'))
            BOT_ID = user.get('id')
    print('loop completed')
else:
    print("could not find bot user with the name " + BOT_NAME)

# starterbot's ID as an environment variable
#BOT_ID = os.environ.get("BOT_ID")

# constants
AT_BOT = "<@" + BOT_ID + ">"
EXAMPLE_COMMAND = "do"

# instantiate Slack & Twilio clients
slack_client = SlackClient(SLACK_BOT_TOKEN)


def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                print('>>>' + str(output))
                return output['text'].split(AT_BOT)[1].strip(), \
                       output['channel']
    return None, None

class StateMachine:
    
    def __init__(self):
        self.guess_history = []
        self.current_state = InitialState()
        self.READ_WEBSOCKET_DELAY = 1 # 1 second delay
        
    def run(self):
        if slack_client.rtm_connect():
            print("WeatherBot connected and running!")
            while True:
                command, channel = parse_slack_output(slack_client.rtm_read())
                if command and channel:
                    print('com:' + str(command))
                    print('chan:' + str(channel))
                    self.guess_history.append(command)
                    self.current_state = self.current_state.handle_command(command, channel)
                    if self.current_state == None:
                        print('Quitting')
                        break
                time.sleep(self.READ_WEBSOCKET_DELAY)
        else:
            print("Connection failed. Invalid Slack token or bot ID?")

class State:
    observation = ""
    city = ""
    resp_dict = ""
    def handle_command(self, command, channel):
        assert 0, 'handle command not implemented'
    
class InitialState(State):
    
    def __init__(self):
        print('creating InitalState')

    def handle_command(self, command, channel):
        print('InitialState receiving ' + command)
        
        for chunk in nltk.ne_chunk(nltk.pos_tag(nltk.word_tokenize(command))):
            print(chunk)
            if hasattr(chunk, 'label'):
                State.city = ' '.join(c[0] for c in chunk.leaves()) # Find the city and return it  
                
        try:          
            State.observation = owm.weather_at_place(State.city) # observation is for the current weather only
            return basicWeather.handle_command(self, command, channel) # Go to next state with the weather observation
        except:
            response = ("Sorry, I can't find a city in this sentence: " 
                        + command 
                        + ". Please rephrase it!")
            slack_client.api_call('chat.postMessage', channel=channel, text=response, as_user=True)
            return InitialState() # Wasn't possible to get a city, return to initial state, offer second try

class basicWeather(State):
    def handle_command(self, command, channel):    
        print('BasicWeatherState receiving ' + State.city)

        weather = State.observation.get_weather() # Get the current weather
        weather_beautify = weather.to_JSON()
        State.resp_dict = json.loads(weather_beautify) # Translate JSON object into python diction
        print(State.resp_dict)
        
        ###
        # Get fields and add description
        ###
        
        # Basic information
        reference_timestamp = State.resp_dict['reference_time']
        # Temperatures are returned in Kelvin
        status = "Overall status: " + State.resp_dict['status']
        temperature_min_k = float(State.resp_dict['temperature']['temp_min'])
        temperature_avg_k = float(State.resp_dict['temperature']['temp'])
        temperature_max_k = float(State.resp_dict['temperature']['temp_max'])
        
        # Temperatures in Celsius, rounded to 1/10
        temperature_min_c = round((temperature_min_k - 273.15),1)
        temperature_avg_c = round((temperature_avg_k - 273.15),1)
        temperature_max_c = round((temperature_max_k - 273.15),1)
        
        # Temperatures in Fahrenheit, rounded to 1/10
        temperature_min_f = round((temperature_min_k * (9/5) - 459.67),1)
        temperature_avg_f = round((temperature_avg_k * (9/5) - 459.67),1)
        temperature_max_f = round((temperature_max_k * (9/5) - 459.67),1)
        
        # Temperatures Final Output
        temperature_min_out = ("The minimum temperature is: " 
                               + str(temperature_min_f) 
                               + "F (" 
                               + str(temperature_min_c) 
                               + "C)")
        temperature_avg_out = ("The average temperature is: " 
                               + str(temperature_avg_f) 
                               + "F (" 
                               + str(temperature_avg_c) 
                               + "C)") 
        temperature_max_out = ("The maximum temperature is: " 
                               + str(temperature_max_f) 
                               + "F (" 
                               + str(temperature_max_c) 
                               +"C)")
        
        # Turn reference timestamp into readable time
        reference_datetime = (datetime.datetime.fromtimestamp(int(reference_timestamp)))
        current_time = datetime.datetime.now()
        difference = new_time = current_time - reference_datetime
        time_diff_seconds = difference.seconds
        time_out = int(time_diff_seconds / 60)
                
        #Build response out of given information
        response = ("The current weather in " 
                    + State.city 
                    + " :\n" 
                    + status
                    + "\n" 
                    + temperature_min_out 
                    + "\n" 
                    + temperature_avg_out
                    + "\n" 
                    + temperature_max_out
                    + "\n"
                    + "The last time we checked the weather here was "
                    + str(time_out)
                    + " minutes ago. \n"
                    + "Do you want more detailed information? Type @weatherbot yes for more, or @weatherbot no to return!")
  
        slack_client.api_call('chat.postMessage', channel=channel, text=response, as_user=True) # Respond with current weather
        return followUp() # Return followUp state, give choice of more info or return to InitialState

class advancedWeather(State):
    def handle_command(self, command, channel):
        print('advancedWeather receiving ' + State.city)

        ###
        # Get fields and add description
        ###
        
        # Advanced Information
        sunset_timestamp = State.resp_dict['sunset_time']
        sunrise_timestamp = State.resp_dict['sunrise_time']
        reference_timestamp = State.resp_dict['reference_time']
        visibility = State.resp_dict['visibility_distance']
        status_detail = State.resp_dict['detailed_status']
        humidity = State.resp_dict['humidity']
        wind_degree = State.resp_dict['wind']['deg']
        wind_speed = State.resp_dict['wind']['speed']
        pressure = State.resp_dict['pressure']['press']
        
        # Turn timestamps into readable time
        sunset_datetime = (" sets tonight at: " 
                          + datetime.datetime.fromtimestamp(int(sunset_timestamp)).strftime('%H:%M:%S'))
        sunrise_datetime = ("Sun rises today at: " 
                           + datetime.datetime.fromtimestamp(int(sunrise_timestamp)).strftime('%H:%M:%S'))
        reference_datetime = (datetime.datetime.fromtimestamp(int(reference_timestamp)))
        current_time = datetime.datetime.now()
        difference = new_time = current_time - reference_datetime
        time_diff_seconds = difference.seconds
        time_out = int(time_diff_seconds / 60)

        # Convert visibility distance to km and mi
        visibility_km = round((visibility / 1000),1)
        visibility_mi = round((visibility * 0.00062137),1)
        visibility_out = ("The current visibility distance is: "
                         + str(visibility_mi)
                         + " miles ("
                         + str(visibility_km)
                         + " km)")
        # Build answer
        response = ("The sun in "
                    + State.city
                    + sunset_datetime 
                    + "\n" 
                    + sunrise_datetime 
                    + "\n" 
                    + visibility_out
                    + ". \n"
                    + "The humidity is: "
                    + str(humidity)
                    + "%. \n"
                    + "The wind blows with a speed of: "
                    + str(wind_speed)
                    + " m/s. \n"
                    + "Currently the air pressure is: "
                    + str(pressure)
                    + " hPa. \n"
                    + "Overall: "
                    + status_detail
                    + ". \n"
                    + "The last time we checked was "
                    + str(time_out)
                    + " minutes ago. \n"
                    + "If you want weather information for another city, you can ask me right away!")
        
        slack_client.api_call('chat.postMessage', channel=channel, text=response, as_user=True)
        
        State.city = ""
        State.obswervation = ""
        State.resp_dict = ""
        
        return InitialState() # All done, go back to InitialState and wait for new input
    
class followUp(State):
    def handle_command(self, command, channel):
        print('FollowUpState receiving ' + command)
        print(State.observation)

        answerYes = ['Yes', 'yes', 'yep', 'yup', 'yea', 'y', 'Yep']
        answerNo = ['No', 'no', 'nope', 'naw', 'Nope', 'n']
        if command in answerYes:
            return advancedWeather()
        if command in answerNo:
            response_no = 'Okay! Do you want to check the weather somewhere else?'
            slack_client.api_call('chat.postMessage', channel=channel, text=response_no, as_user=True)
            return InitialState()
        if (command not in answerYes or command not in answerNo):
            response_unknown = 'Sorry, I did not understand that answer. Can you rephrase that?'
            slack_client.api_call('chat.postMessage', channel=channel, text=response_unknown, as_user=True)
            return followUp()

if __name__ == "__main__":
    weather = StateMachine()
    weather.run()