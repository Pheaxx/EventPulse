from rest_framework.test import APITestCase
from rest_framework import HTTP_HEADER_ENCODING
from rest_framework import status
from django.urls import reverse
from django.contrib.auth.models import User
from apps.eventpulse.models import UserHmac
import base64

from apps.eventpulse.utils import is_valid_hmac_notification, generate_notification_sig

class RelaySettingsTest(APITestCase):
    def setUp(self):
        # create test user
        self.user = User.objects.create_user(username='testuser', password='testpass')

        # test hmac key
        self.hmac_key = "b8e4d3fcf2a1949db515d6cfdcf4c44f82c2e5574c60a10f999f93e76300e4f2"

        # save test hmac_key
        UserHmac.objects.create(user=self.user, hmac_key=self.hmac_key)

        # test payload
        self.payload = {
            "live": "false",
            "notificationItems": [
                {
                    "NotificationRequestItem": {
                        "additionalData": {
                            "expiryDate": "03/2030",
                            "authCode": "076314",
                            "cardSummary": "0002",
                            "cardHolderName": "Macauly Dean",
                            "threeds2.cardEnrolled": "false",
                            "checkout.cardAddedBrand": "amex",
                            "hmacSignature": "8cRl76ajqL3j6c8jJiSbYVIg9bBlxOVQ6mS0zuHsAIU="
                        },
                        "amount": {
                            "currency": "EUR",
                            "value": 3179400
                        },
                        "eventCode": "AUTHORISATION",
                        "eventDate": "2025-06-03T21: 27: 40+02: 00",
                        "merchantAccountCode": "JustAHobbyProjectECOM",
                        "merchantReference": "PLAYGROUND-1748978860503",
                        "operations": [
                            "CANCEL",
                            "CAPTURE",
                            "REFUND"
                        ],
                        "paymentMethod": "amex",
                        "pspReference": "BHP92XTBGJ522P75",
                        "reason": "076314: 0002: 03/2030",
                        "success": "true"
                    }
                }
            ]
        }

        # create credentials
        self.credentials = base64.b64encode('testuser:testpass'.encode(HTTP_HEADER_ENCODING)).decode(HTTP_HEADER_ENCODING)

    def test_event(self):
        url = reverse('eventpulse:events')


        # post data
        response = self.client.post(
            url,
            self.payload,
            format='json',
            HTTP_AUTHORIZATION=f'Basic {self.credentials}',
            **{'HTTP_HOST':'127.0.0.1:8000'}
        )

        # check status code
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    # test to check if HMAC is correctly made and equal to what is expected
    def test_generate_notification_sig(self):
        generated_sig = generate_notification_sig(self.payload['notificationItems'][0]['NotificationRequestItem'], self.hmac_key)
        generated_sig_str = generated_sig.decode("utf-8")
        self.assertEqual(generated_sig_str, self.payload['notificationItems'][0]['NotificationRequestItem']['additionalData']['hmacSignature'])

    # test to check if HMAC is correctly made and equal to True with what is supplied
    def test_is_valid_hmac_notification(self):
        test_is_valid_hmac_notification = is_valid_hmac_notification(self.payload, self.hmac_key)
        self.assertTrue(test_is_valid_hmac_notification[0])
        self.assertEqual(test_is_valid_hmac_notification[1],test_is_valid_hmac_notification[2])


