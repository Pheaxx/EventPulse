from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from apps.eventpulse.models import Events, RelaySettings
from apps.eventpulse.utils import create_log
import json
import requests
from requests.exceptions import RequestException
from django.conf import settings
import time


@shared_task(bind=True, max_retries=5)
def process_transaction(self, event_id, failed_relay_ids=None):
    try:

        # get event based on uuid and set variables
        event = Events.objects.get(uuid=event_id)
        transaction_data = event.payload['notificationItems'][0]['NotificationRequestItem']
        event_code = transaction_data['eventCode']

        # get relay settings based on event_code
        relay_settings = RelaySettings.objects.filter(event_code=event_code)

        # if no relay settings exists, create log entry and return task result as False
        if not relay_settings.exists():
            create_log({"uuid": event_id, "level": "ERROR",
                      "message": {"error": f"No relay settings found for event {event_id} with event code {event_code}"}})
            return False

        # if additionalData is not in the event, create log entry and return result as False =
        if 'additionalData' not in transaction_data:
            create_log({"uuid": event_id, "level": "ERROR",
                      "message": {"error": f"No additional data found for event {event_id} with event code {event_code}"}})
            return False

    # if Exception is raised, create log entry  and set task for retry
    except Exception as e:
        create_log({"uuid": event_id, "level": "ERROR",
                  "message": {"error": f"Error processing event {event_id}: {str(e)}"}})
        # Retry with exponential backoff
        retry_countdown = 2 ** self.request.retries  # 1, 2, 4, 8, 16 seconds
        self.retry(exc=e, countdown=retry_countdown)

    # update event with relay settings
    event.relay_settings_fk.set(relay_settings)

    # set reference to either originalReference or pspReference when event_code is equal to CANCELLATION
    reference = transaction_data['originalReference'] if event_code=='CANCELLATION' else transaction_data['pspReference']

    # define message to be relayed
    relay_message = {
        "eventCode": event_code,
        "timestamp": transaction_data['eventDate'],
        "url": f"https://ca-test.adyen.com/ca/ca/accounts/showTx.shtml?pspReference={reference}&txType=Payment",
        "payload": {
            "originalPspReference": transaction_data['originalReference'] if 'originalReference' in transaction_data else None,
            "pspReference": transaction_data['pspReference'],
            "amount": {
              "value": transaction_data['amount']['value'],
              "currency": transaction_data['amount']['currency']
            },
            "paymentMethod": transaction_data['paymentMethod'],
            "card": {
                "bin": transaction_data['additionalData']['cardHolderName'] if 'cardHolderName' in transaction_data['additionalData'] else None,
                "last4": transaction_data['additionalData']['cardSummary'] if 'cardSummary' in transaction_data['additionalData'] else None,
                "expiry": transaction_data['additionalData']['expiryDate'] if 'expiryDate' in transaction_data['additionalData'] else None,
            },
            "merchantAccount": transaction_data['merchantAccountCode'],
            "success": transaction_data['success'],
        }
    }

    # create payload
    payload = {"content": f"```json\n{json.dumps(relay_message, indent=4)}```"}

    # set task success and retry variables
    success = False
    failed_relays = []
    
    # if we're in a retry, only process the failed relay settings
    if failed_relay_ids:
        relay_settings = relay_settings.filter(id__in=failed_relay_ids)
        create_log({
            "uuid": event_id,
            "level": "INFO", 
            "message": {"retry_attempt": self.request.retries, "retrying_relay_count": len(failed_relay_ids)}
        })

    # for each relay setting, execute relay
    for relay_setting in relay_settings:
        try:
            # set a timeout to prevent hanging connections
            result = requests.post(
                relay_setting.forward_url, 
                data=payload,
                timeout=10  # 10 seconds timeout
            )

            # check if status code is of HTTP 2xx and set success to True and create log entry
            if result.status_code in [200, 201, 202, 204]:
                success = True
                create_log({
                    "uuid": event_id,
                    "level": "INFO", 
                    "message": {
                        "status": "success",
                        "relay": relay_setting.name,
                        "response_code": result.status_code
                    }
                })
            else:
                # if status code is not of HTPP 2xx, append failed relay to failed list and create log entry
                failed_relays.append({
                    "id": relay_setting.id,
                    "relay_name": relay_setting.name,
                    "status_code": result.status_code,
                    "response": result.text[:100]  # Truncate long responses
                })
                create_log({
                    "uuid": event_id,
                    "level": "WARNING", 
                    "message": {
                        "status": "failed",
                        "relay": relay_setting.name,
                        "response_code": result.status_code,
                        "response": result.text[:100]
                    }
                })
        except RequestException as e:
            # if exception is raised, append failed relay to failed list and create log entry
            failed_relays.append({
                "id": relay_setting.id,
                "relay_name": relay_setting.name,
                "error": str(e)
            })
            create_log({
                "uuid": event_id,
                "level": "ERROR", 
                "message": {
                    "status": "exception",
                    "relay": relay_setting.name,
                    "error": str(e)
                }
            })
    
    # if any relays failed, retry the task with exponential backoff
    if failed_relays:
        # mark the event for retry
        event.retry = True
        event.save()
        
        # prepare error message
        error_msg = f"Failed to relay to {len(failed_relays)} destinations"
        create_log({
            "uuid": event_id,
            "level": "WARNING", 
            "message": {
                "retry_scheduled": True,
                "failed_relays": failed_relays,
                "retry_count": self.request.retries
            }
        })
        
        # get IDs of failed relays for selective retry
        failed_relay_ids = [relay['id'] for relay in failed_relays]
        
        # retry with exponential backoff if we haven't exceeded max retries
        # cap retries at one (1) hour
        try:
            retry_countdown = min(2 ** self.request.retries * 60, 3600)
            raise self.retry(
                exc=Exception(error_msg), 
                countdown=retry_countdown,
                kwargs={'failed_relay_ids': failed_relay_ids}
            )
        except MaxRetriesExceededError:
            create_log({
                "uuid": event_id,
                "level": "ERROR", 
                "message": {
                    "status": "max_retries_exceeded",
                    "failed_relays": failed_relays
                }
            })
            #TODO implement a fallback strategy or alert mechanism
    else:
        # all relays succeeded, mark the event as processed
        event.processed = True
        event.retry = False
        event.save()

    return success