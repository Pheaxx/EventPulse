from celery import shared_task
from apps.eventpulse.models import Events, RelaySettings
from apps.eventpulse.utils import create_log
import json
import requests

@shared_task
def process_payment(event_id):
    # get event
    event = Events.objects.get(event_id=event_id)

    # get relay settings
    payment_data = event.payload
    payment_type = payment_data['data']['type']
    payment_status = payment_data['data']['status']

    # get relay settings
    relay_settings = RelaySettings.objects.filter(type=payment_type, status=payment_status)

    # update event with relay settings
    event.relay_settings_id.set(relay_settings)

    # message to be relayed
    relay_message = f"""
    New Transaction
    
    Type: {payment_type}
    Status: {payment_status}
    Direction: {payment_data['data']['direction']}
    To: {payment_data['data']['counterparty']['merchant']['name']}
    Amount: {payment_data['data']['amount']['value']}
    Currency: {payment_data['data']['amount']['currency']}
    Date: {payment_data['data']['creationDate']}
    Reference: {payment_data['data']['reference']}
    """
    payload = {"content": relay_message}
    for relay_setting in relay_settings:
        requests.post(relay_setting.forward_url,data=payload)
        create_log({"event_id": event_id, "level": "INFO", "message": {"Relayed message to":relay_setting.name}})