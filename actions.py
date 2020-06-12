from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher

from typing import Dict, Text, Any, List

import requests
from rasa_sdk import Action
from rasa_sdk.events import SlotSet, FollowupAction
from rasa_sdk.forms import FormAction

#from actions import keys
#from actions import medical
import keys
import medical


CATEGORY_TYPES = {
    "machine_learning":
        {
            "name": "machine learning",
            "resource": "MACHINELEARNING"
        },
    "statistical_analysis":
        {
            "name": "statistical analysis",
            "resource": "STATISTICALANALYSIS"
        },
    "software_consulting":
        {
            "name": "software consulting",
            "resource": "SOFTWARECONSULTING"
        }
}

class WhatToLearnCategoryTypes(Action):
    """This action class allows to display buttons for each category type
    for the user to chose from to fill the category_type entity slot."""

    def name(self) -> Text:
        """Unique identifier of the action"""

        return "find_what_to_learn_category"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List:

        buttons = []
        for t in CATEGORY_TYPES:
            category_type = CATEGORY_TYPES[t]
            payload = "/inform{\"category_type\": \"" + category_type.get(
                "resource") + "\"}"

            buttons.append(
                {"title": "{}".format(category_type.get("name").title()),
                 "payload": payload})
        
        dispatcher.utter_message(text = "Which would you like more information on: ", buttons = buttons)

        return []

class DisplayDescription(Action):
    """This action class will display description."""

    def name(self) -> Text:
        """Unique identifier of the action"""

        return "find_category_description"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List:

            category_type = tracker.get_slot('category_type')

            if category_type == "MACHINELEARNING":
                dispatcher.utter_message("""Neuralocity provides unique machine learning solution
                    in predicting customer behavior and outcomes. We can use natural language processing
                    to better understand your customers.""")
            elif category_type == "STATISTICALANALYSIS":
                dispatcher.utter_message("""We have many years of applying predictive analytics, choice
                modeling, segmentation, and optimization.""")
            else:
                dispatcher.utter_message("""We provide customer software solutions that can be 
                standalone, SaaS, or mobile.""")

            return []



def extract_metadata_from_tracker(tracker):
    events = tracker.current_state()['events']
    user_events = []
    for e in events:
        if e['event'] == 'user':
            user_events.append(e)

    return user_events[-1]['metadata']            

class FindWeather(Action):
    """This action class will display description."""

    def name(self) -> Text:
        """Unique identifier of the action"""

        return "find_weather"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List:

            userIP = extract_metadata_from_tracker(tracker)

            ip = userIP["ipaddress"]

            full_path = f"https://ipinfo.io/{ip}?token={keys.IPINFO}"

            results = requests.get(full_path).json()

            location = results['loc']
            city = results['city']
            postal = results['postal']

            locations = location.split(",")
            lat = locations[0]
            lon = locations[1]

            api_path = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={keys.WEATHERAPI}&units=imperial"

            results = requests.get(api_path).json()

            temperature = results['main']['temp']
            humidity = results['main']['humidity']
            description = results['weather'][0]['description']

            message = "Current temperature is " + str(temperature) + "\u00b0 F with " + str(humidity) + "% humidity. " + description.capitalize() + ". "

            if temperature < 50:
                message += "I would recommend a coat. "            
            elif temperature < 75:
                message += "I would recommend a jacket. "
            else:
                message += "I would recommend shorts. "

            if 'rain' in description.lower():
                message += "You might want to take an umbrella."

            icon = results['weather'][0]['icon']
            iconurl = "https://openweathermap.org/img/w/" + icon + ".png";

            dispatcher.utter_message(message, image=iconurl)

            return []

class FindBestTypes(Action):
    """This action class allows to display buttons for each facility type
    for the user to chose from to fill the facility_type entity slot."""

    def name(self) -> Text:
        """Unique identifier of the action"""

        return "find_best_type"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List:

        place = tracker.get_slot('place')

        userIP = extract_metadata_from_tracker(tracker)
        
        ip = userIP['ipaddress']

        full_path = f"https://ipinfo.io/{ip}?token={keys.IPINFO}"

        results = requests.get(full_path).json()

        location = results['loc']

        #city = results['city']
        #postal = results['postal']

        #location = "33.307575,-111.844940"

        target = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

        params = {
            "location": location,
            "radius": 5000,
            "type": place,
            "key": keys.GOOGLEAPI
        }

        response = requests.get(target, params=params)

        found = response.json()

        best_list = []
        for place in found['results']:
            if 'rating' in place:
                best_list.append(place)

        best_list = sorted(best_list, key = lambda i: i['rating'], reverse=True)

        best_list = best_list[:3]

        for place in best_list:
            message = ""
            message += place['name']
            message += ", " + place['vicinity']
            message += ", Rating: " + str(place['rating'])

            dispatcher.utter_message(message)

        return []

