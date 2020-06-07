## saying_hello
* greet
    - utter_greet

## happy_path
* medical
    - find_facility_types
* inform{"facility_type": "xubh-q36u"}    
    - facility_form
    - form{"name": "facility_form"}
    - form{"name": null}
* inform{"facility_id": 4245}
    - find_healthcare_address
    - utter_address
* thanks
    - utter_noworries

## happy_path_multi_requests
* medical
    - find_facility_types
* inform{"facility_type": "xubh-q36u"}
    - facility_form
    - form{"name": "facility_form"}
    - form{"name": null}
* inform{"facility_id": "747604"}
    - find_healthcare_address
    - utter_address
* search_provider{"facility_type": "xubh-q36u"}
    - facility_form
    - form{"name": "facility_form"}
    - form{"name": null}
* inform{"facility_id": 4245}   
    - find_healthcare_address
    - utter_address

## happy_path2
* search_provider{"location": "Austin", "facility_type": "xubh-q36u"}
    - facility_form
    - form{"name": "facility_form"}
    - form{"name": null}
* inform{"facility_id": "450871"}
    - find_healthcare_address
    - utter_address
* thanks
    - utter_noworries

## ask_what_is_neuralocity
* faq_ask_what_is_neuralocity
    - utter_faq_ask_what_is_neuralocity

## story_goodbye
* goodbye
    - utter_goodbye

## story_thankyou
* thanks
    - utter_noworries

## what_technologies
* what_technologies
    - utter_what_technologies

## faq_ask_about_pricing
* faq_ask_about_pricing
    - utter_faq_pricing

## talk_to_someone
* talk_to_someone
    - utter_talk_to_someone

## story_utter_out_of_scope
* out_of_scope
    - utter_out_of_scope

## are_you_real
* who_are_you
    - utter_i_am

## joke
* say_something_funny
    - utter_joke
