from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher

from typing import Dict, Text, Any, List

import requests
from rasa_sdk import Action
from rasa_sdk.events import SlotSet, FollowupAction
from rasa_sdk.forms import FormAction

from actions import keys

# We use the medicare.gov database to find information about 3 different
# healthcare facility types, given a city name, zip code or facility ID
# the identifiers for each facility type is given by the medicare database
# xubh-q36u is for hospitals
# b27b-2uc7 is for nursing homes
# 9wzi-peqs is for home health agencies

ENDPOINTS = {
    "base": "https://data.medicare.gov/resource/{}.json",
    "xubh-q36u": {
        "city_query": "?city={}",
        "zip_code_query": "?zip_code={}",
        "id_query": "?provider_id={}"
    },
    "b27b-2uc7": {
        "city_query": "?provider_city={}",
        "zip_code_query": "?provider_zip_code={}",
        "id_query": "?federal_provider_number={}"
    },
    "9wzi-peqs": {
        "city_query": "?city={}",
        "zip_code_query": "?zip={}",
        "id_query": "?provider_number={}"
    }
}

FACILITY_TYPES = {
    "hospital":
        {
            "name": "hospital",
            "resource": "xubh-q36u"
        },
    "nursing_home":
        {
            "name": "nursing home",
            "resource": "b27b-2uc7"
        },
    "home_health":
        {
            "name": "home health agency",
            "resource": "9wzi-peqs"
        }
}


def _create_path(base: Text, resource: Text,
                 query: Text, values: Text) -> Text:
    """Creates a path to find provider using the endpoints."""

    if isinstance(values, list):
        return (base + query).format(
            resource, ', '.join('"{0}"'.format(w) for w in values))
    else:
        return (base + query).format(resource, values)


def _find_facilities(location: Text, resource: Text) -> List[Dict]:
    """Returns json of facilities matching the search criteria."""

    if str.isdigit(location):
        full_path = _create_path(ENDPOINTS["base"], resource,
                                 ENDPOINTS[resource]["zip_code_query"],
                                 location)
    else:
        full_path = _create_path(ENDPOINTS["base"], resource,
                                 ENDPOINTS[resource]["city_query"],
                                 location.upper())
    #print("Full path:")
    #print(full_path)
    results = requests.get(full_path).json()
    return results


def _resolve_name(facility_types, resource) ->Text:
    for key, value in facility_types.items():
        if value.get("resource") == resource:
            return value.get("name")
    return ""


class FindFacilityTypes(Action):
    """This action class allows to display buttons for each facility type
    for the user to chose from to fill the facility_type entity slot."""

    def name(self) -> Text:
        """Unique identifier of the action"""

        return "find_facility_types"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List:

        buttons = []
        for t in FACILITY_TYPES:
            facility_type = FACILITY_TYPES[t]
            payload = "/inform{\"facility_type\": \"" + facility_type.get(
                "resource") + "\"}"

            buttons.append(
                {"title": "{}".format(facility_type.get("name").title()),
                 "payload": payload})

        # TODO: update rasa core version for configurable `button_type`

        dispatcher.utter_message(template = "utter_medical", buttons = buttons)
        return []


class FindHealthCareAddress(Action):
    """This action class retrieves the address of the user's
    healthcare facility choice to display it to the user."""

    def name(self) -> Text:
        """Unique identifier of the action"""

        return "find_healthcare_address"

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict]:

        facility_type = tracker.get_slot("facility_type")
        healthcare_id = tracker.get_slot("facility_id")
        full_path = _create_path(ENDPOINTS["base"], facility_type,
                                 ENDPOINTS[facility_type]["id_query"],
                                 healthcare_id)
        results = requests.get(full_path).json()
        if results:
            selected = results[0]
            if facility_type == FACILITY_TYPES["hospital"]["resource"]:
                address = "{}, {}, {} {}".format(selected["address"].title(),
                                                 selected["city"].title(),
                                                 selected["state"].upper(),
                                                 selected["zip_code"].title())
            elif facility_type == FACILITY_TYPES["nursing_home"]["resource"]:
                address = "{}, {}, {} {}".format(selected["provider_address"].title(),
                                                 selected["provider_city"].title(),
                                                 selected["provider_state"].upper(),
                                                 selected["provider_zip_code"].title())
            else:
                address = "{}, {}, {} {}".format(selected["address"].title(),
                                                 selected["city"].title(),
                                                 selected["state"].upper(),
                                                 selected["zip"].title())

            return [SlotSet("facility_address", address)]
        else:
            print("No address found. Most likely this action was executed "
                  "before the user choose a healthcare facility from the "
                  "provided list. "
                  "If this is a common problem in your dialogue flow,"
                  "using a form instead for this action might be appropriate.")

            return [SlotSet("facility_address", "not found")]


class FacilityForm(FormAction):
    """Custom form action to fill all slots required to find specific type
    of healthcare facilities in a certain city or zip code."""

    def name(self) -> Text:
        """Unique identifier of the form"""

        return "facility_form"

    @staticmethod
    def required_slots(tracker: Tracker) -> List[Text]:
        """A list of required slots that the form has to fill"""

        return ["facility_type", "location"]

    def slot_mappings(self) -> Dict[Text, Any]:
        return {"facility_type": self.from_entity(entity="facility_type",
                                                  intent=["inform",
                                                          "search_provider"]),
                "location": self.from_entity(entity="location",
                                             intent=["inform",
                                                     "search_provider"])}

    def submit(self,
               dispatcher: CollectingDispatcher,
               tracker: Tracker,
               domain: Dict[Text, Any]
               ) -> List[Dict]:
        """Once required slots are filled, print buttons for found facilities"""

        location = tracker.get_slot('location')
        facility_type = tracker.get_slot('facility_type')

        results = _find_facilities(location, facility_type)
        button_name = _resolve_name(FACILITY_TYPES, facility_type)
        if len(results) == 0:
            dispatcher.utter_message(
                "Sorry, we could not find a {} in {}.".format(button_name,
                                                              location.title()))
            return []

        buttons = []
        # limit number of results to 3 for clear presentation purposes
        for r in results[:3]:
            if facility_type == FACILITY_TYPES["hospital"]["resource"]:
                facility_id = r.get("provider_id")
                name = r["hospital_name"]
            elif facility_type == FACILITY_TYPES["nursing_home"]["resource"]:
                facility_id = r["federal_provider_number"]
                name = r["provider_name"]
            else:
                facility_id = r["provider_number"]
                name = r["provider_name"]

            payload = "/inform{\"facility_id\":\"" + facility_id + "\"}"
            buttons.append(
                {"title": "{}".format(name.title()), "payload": payload})

        if len(buttons) == 1:
            message = "Here is a {} near you:".format(button_name)
        else:
            if button_name == "home health agency":
                button_name = "home health agencie"
            message = "Here are {} {}s near you:".format(len(buttons),
                                                         button_name)

        # TODO: update rasa core version for configurable `button_type`
        dispatcher.utter_message(text = message, buttons = buttons)

        return []

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

            api_path = f"api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={keys.WEATHERAPI}&units=imperial"

            results = requests.get(api_path).json()

            temperature = results['main']['temp']
            humidity = results['main']['humidity']
            description = results['weather'][0]['description']

            message = "Current temperature is " + str(temperature) + "\u00b0F with " + str(humidity) + "% humidity. " + description + ". "

            if temperature < 50:
                message += "I would recommend a coat. "            
            elif temperature < 75:
                message += "I would recommend a jacket. "
            else:
                message += "I would recommend sunscreen. "

            if 'rain' in description.lower():
                message += "You might want to take an umbrella."

            icon = results['weather'][0]['icon']
            iconurl = "http://openweathermap.org/img/w/" + icon + ".png";

            dispatcher.utter_message(message, image=iconurl)

            return []



 




            
