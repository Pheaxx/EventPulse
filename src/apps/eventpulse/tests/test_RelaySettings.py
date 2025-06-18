from rest_framework.test import APITestCase
from rest_framework import HTTP_HEADER_ENCODING
from rest_framework import status
from django.urls import reverse
from apps.eventpulse.models import RelaySettings
from django.contrib.auth.models import User
import base64

class RelaySettingsTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.credentials = base64.b64encode('testuser:testpass'.encode(HTTP_HEADER_ENCODING)).decode(HTTP_HEADER_ENCODING)

    def test_create_relay_settings(self):
        data = {
            "name": "Test RelaySetting",
            "description": "Test RelaySetting",
            "source_host": "127.0.0.1",
            "forward_url": "TestURL",
            "event_code":"TestType",
        }

        # define url
        url = reverse("eventpulse:relay-settings-get-post")

        # post data
        response = self.client.post(url, data, format='json', HTTP_AUTHORIZATION=f'Basic {self.credentials}')

        # check status code
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check if object has been created
        self.assertIsNotNone(RelaySettings.objects.get())

        # get created object
        db_entry = RelaySettings.objects.get()

        # check fields with post data
        self.assertEqual(db_entry.name, data["name"])
        self.assertEqual(db_entry.description, data["description"])
        self.assertEqual(db_entry.source_host, data["source_host"])
        self.assertEqual(db_entry.forward_url, data["forward_url"])
        self.assertEqual(db_entry.event_code, data["event_code"])

    def test_get_relay_settings(self):
        # create two test objects
        RelaySettings.objects.create(
                name ="Test RelaySetting 1",
                description = "Test Settings",
                source_host = "127.0.0.1",
                forward_url = "TestURL",
                event_code = "TestEventCode",


        )
        RelaySettings.objects.create(
            name="Test RelaySetting 2",
            description="Test Settings",
            source_host="127.0.0.1",
            forward_url="TestURL",
            event_code="TestEventCode",

        )
        db_entries = RelaySettings.objects.all()

        # define url
        url = reverse('eventpulse:relay-settings-get-post')

        # make get request
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=f'Basic {self.credentials}')
        response_json = response.json()
        # check status code
        self.assertEqual(response.status_code,status.HTTP_200_OK)

        # check if all objects are returned
        self.assertEqual(len(response.json()), 2)

        # check if what is returns, contains the data that has been created
        self.assertEqual(response_json[0]['relay_id'], str(db_entries[0].relay_id))
        self.assertEqual(response_json[0]['name'], db_entries[0].name)
        self.assertEqual(response_json[0]['description'], db_entries[0].description)
        self.assertEqual(response_json[0]['source_host'], db_entries[0].source_host)
        self.assertEqual(response_json[0]['forward_url'], db_entries[0].forward_url)
        self.assertEqual(response_json[0]['event_code'], db_entries[0].event_code)

        self.assertEqual(response_json[1]['relay_id'], str(db_entries[1].relay_id))
        self.assertEqual(response_json[1]['name'], db_entries[1].name)
        self.assertEqual(response_json[1]['description'], db_entries[1].description)
        self.assertEqual(response_json[1]['source_host'], db_entries[1].source_host)
        self.assertEqual(response_json[1]['forward_url'], db_entries[1].forward_url)
        self.assertEqual(response_json[1]['event_code'], db_entries[1].event_code)

    def test_delete_relay_setting(self):

        # create test object
        data = RelaySettings.objects.create(
            name="Test RelaySetting",
            description="Test Settings",
            source_host="127.0.0.1",
            forward_url="TestURL",
            event_code = "TestEventCode",

        )
        # define url with param
        url = reverse('eventpulse:relay-setting-get-del', kwargs={'relay_id':data.relay_id})

        # make delete request
        response = self.client.delete(url, format='json', HTTP_AUTHORIZATION=f'Basic {self.credentials}')

        # check if created
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_get_detail_relay_setting(self):
        # create test object
        data = RelaySettings.objects.create(
            name="Test Detail RelaySetting",
            description="Test Settings",
            source_host="127.0.0.1",
            forward_url="TestURL",
            event_code = "TestEventCode",

        )

        # define url with param
        url = reverse('eventpulse:relay-setting-get-del', kwargs={'relay_id': data.relay_id})

        # make post request
        response = self.client.get(url, format='json', HTTP_AUTHORIZATION=f'Basic {self.credentials}')
        response_json = response.json()
        # check if created
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check if endpoint returns 9 fields
        self.assertEqual(len(response.json()), 8)

        # check if what is returns, contains the data that has been created
        self.assertEqual(response_json['relay_id'], str(data.relay_id))
        self.assertEqual(response_json['name'], data.name)
        self.assertEqual(response_json['description'], data.description)
        self.assertEqual(response_json['source_host'], data.source_host)
        self.assertEqual(response_json['forward_url'], data.forward_url)
        self.assertEqual(response_json['event_code'], data.event_code)




