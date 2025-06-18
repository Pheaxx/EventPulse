from rest_framework import serializers
from .models import Events, Log,RelaySettings

class ChoiceFieldWithChoices(serializers.ChoiceField):
    def run_validation(self, data):
        try:
            return super().run_validation(data)
        except serializers.ValidationError as e:
            # Add the list of available choices to the error
            choices_list = list(self.choices)
            raise serializers.ValidationError(
                f"{e.detail[0]} Valid choices are: {choices_list}"
            )

class RelaySettingsSerializer(serializers.ModelSerializer):
    EVENT_CODE_CHOICES = (
        ('AUTHORISATION','AUTHORISATION'),
        ('AUTHORISATION_ADJUSTMENT','AUTHORISATION_ADJUSTMENT'),
        ('CANCELLATION','CANCELLATION'),
        ('CANCEL_OR_REFUND','CANCEL_OR_REFUND'),
        ('CAPTURE','CAPTURE'),
        ('CAPTURE_FAILED','CAPTURE_FAILED'),
        ('EXPIRE','EXPIRE'),
        ('ORDER_CLOSED','ORDER_CLOSED'),
        ('ORDER_OPENED','ORDER_OPENED'),
        ('REFUND','REFUND'),
        ('REFUND_REVERSED','REFUND_REVERSED'),
        ('REFUND_FAILED','REFUND_FAILED'),
        ('REFUND_WITH_DATA','REFUND_WITH_DATA'),
        ('REPORT_AVAILABLE','REPORT_AVAILABLE'),
        ('TECHNICAL_CANCEL','TECHNICAL_CANCEL'),
        ('VOID_PENDING_REFUND','VOID_PENDING_REFUND'),
    )

    uuid = serializers.UUIDField(read_only=True)
    event_code = ChoiceFieldWithChoices(choices=EVENT_CODE_CHOICES)

    class Meta:
        model = RelaySettings
        fields = ['name','description','uuid','event_code','source_host','forward_url','api_key','api_secret']

class EventsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Events
        fields = ['host','payload', 'uuid', 'isvalid_hmac', 'psp_reference', 'event_code', 'retry']

class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ['uuid', 'level', 'message']