from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from .serializers import EventsSerializer, RelaySettingsSerializer
from .models import RelaySettings,Events
import uuid
import copy
from .tasks import ProcessTransaction
from .utils import create_log, is_valid_hmac_notification
from django.conf import settings

# Create your views here.

# incoming events
@api_view(['POST'])
def events(request):
    # create an uuid to be used in events and logs
    event_uuid = uuid.uuid4()

    # get hmac_key
    hmac_key = settings.ADYEN_HMAC_KEY

    # check if hmac is valid
    # using deepcopy as the check deletes the additionalData key
    isvalid_hmac = is_valid_hmac_notification(copy.deepcopy(request.data), hmac_key)

    # extract pspReference and eventCode from the webhook payload
    psp_reference = request.data['notificationItems'][0]['NotificationRequestItem'].get('pspReference', 'unknown'),
    event_code = request.data['notificationItems'][0]['NotificationRequestItem'].get('eventCode', 'unknown'),

    # check if hmac is valid, if not return HTTP 401
    if not isvalid_hmac[0]:
        # create log entry with detailed information about the HMAC failure
        create_log({
            "uuid": event_uuid,
            "level": "ERROR",
            "message": {
                "func": "views.events", 
                "status": "authentication_failed",
                "reason": "HMAC signature validation failed",
                "psp_reference": psp_reference,
                "event_code": event_code,
                "merchant_account": request.data['notificationItems'][0]['NotificationRequestItem'].get('merchantAccountCode', 'unknown'),
                "received_hmac": isvalid_hmac[1],
                "calculated_hmac": isvalid_hmac[2],
                "source_ip": request.META.get('REMOTE_ADDR', 'unknown'),
                "timestamp": request.data['notificationItems'][0]['NotificationRequestItem'].get('eventDate', 'unknown')
            }
        })
        return Response({"message":"HMAC Invalid"},status=status.HTTP_401_UNAUTHORIZED)

    # check for idempotency
    is_duplicate_event = Events.objects.filter(psp_reference=psp_reference,event_code=event_code).exists()

    if is_duplicate_event:
        # if event has been sent before, create log and return 202 to fulfill Adyen's requirement to get an HTTP 202 back
        create_log({
            "uuid": event_uuid,
            "level": "WARNING",
            "message": {
                "status": "duplicate_event",
                "reason": "Event with same psp_reference and event_code already exists",
                "psp_reference": psp_reference,
                "event_code": event_code,
                "merchant_account": request.data['notificationItems'][0]['NotificationRequestItem'].get('merchantAccountCode', 'unknown'),
                "source_ip": request.META.get('REMOTE_ADDR', 'unknown'),
                "timestamp": request.data['notificationItems'][0]['NotificationRequestItem'].get('eventDate', 'unknown')
            }
        })
        return Response(status=status.HTTP_202_ACCEPTED)
    else:
        # if new event, process, validate and save the event data in the database
        event_data = {
            'uuid': event_uuid,
            'host': request.META['HTTP_HOST'],
            'isvalid_hmac': bool(isvalid_hmac[0]),
            'relay_settings_id': [],
            'psp_reference': request.data['notificationItems'][0]['NotificationRequestItem']['pspReference'],
            'event_code': request.data['notificationItems'][0]['NotificationRequestItem']['eventCode'],
            'payload': request.data,
        }

        # validate and save to the database
        serialized_data = EventsSerializer(data=event_data)
        serialized_data.is_valid(raise_exception=True)
        serialized_data.save()

        # create detailed log entry for successful event receipt
        create_log({
            "uuid": event_uuid,
            "level": "INFO", 
            "message": {
                "status": "event_received",
                "psp_reference": psp_reference,
                "event_code": event_code,
                "merchant_account": request.data['notificationItems'][0]['NotificationRequestItem'].get('merchantAccountCode', 'unknown'),
                "amount": request.data['notificationItems'][0]['NotificationRequestItem'].get('amount', {}),
                "success": request.data['notificationItems'][0]['NotificationRequestItem'].get('success', 'unknown'),
                "source_ip": request.META.get('REMOTE_ADDR', 'unknown'),
                "timestamp": request.data['notificationItems'][0]['NotificationRequestItem'].get('eventDate', 'unknown'),
                "payment_method": request.data['notificationItems'][0]['NotificationRequestItem'].get('paymentMethod', 'unknown')
            }
        })

        # celery task ProcessPayment
        ProcessTransaction.process_transaction.delay(event_uuid)

        # return 202 to fulfill acceptance requirement
        return Response(status=status.HTTP_202_ACCEPTED)

class RelaySettingsView(APIView):

    # get all RelaySettings
    def get(self,request):
        webhook_settings = RelaySettings.objects.all()
        serializer = RelaySettingsSerializer(webhook_settings, many=True)
        return Response(serializer.data)

    # post new RelaySettings, return message with newly created RelaySettings
    def post(self,request):
        serializer = RelaySettingsSerializer(data=request.data)
        if serializer.is_valid():
            relay_setting = serializer.save()

            # Log relay setting creation
            create_log({
                "uuid": relay_setting.uuid,
                "level": "INFO", 
                "message": {
                    "action": "relay_setting_created",
                    "relay_id": str(relay_setting.uuid),
                    "name": relay_setting.name,
                    "event_code": relay_setting.event_code,
                    "forward_url": relay_setting.forward_url,
                    "created_by": request.user.username
                }
            })
            return Response({"message":"Webhook Settings saved", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RelaySettingView(APIView):

    # get one RelaySetting based on the UUID
    def get(self,request,relay_id):
        webhook_settings = get_object_or_404(RelaySettings, uuid=relay_id)
        serializer = RelaySettingsSerializer(webhook_settings)
        return Response(serializer.data)

    # delete RelaySetting based on UUID
    def delete(self, request, relay_id):
        item = get_object_or_404(RelaySettings, uuid=relay_id)

        # Log relay setting deletion before deleting
        create_log({
            "uuid": relay_id,
            "level": "INFO", 
            "message": {
                "action": "relay_setting_deleted",
                "relay_id": str(item.uuid),
                "name": item.name,
                "event_code": item.event_code,
                "deleted_by": request.user.username
            }
        })
        item.delete()
        return Response({"message": "Item deleted successfully."}, status=status.HTTP_204_NO_CONTENT)