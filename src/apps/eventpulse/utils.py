from .serializers import LogSerializer
import hmac
import hashlib
import base64
import binascii


# create log
def create_log(log):
    serialized_log = LogSerializer(data=log)
    serialized_log.is_valid(raise_exception=True)
    serialized_log.save()

# HMAC check
def generate_notification_sig(dict_object, hmac_key):
    hmac_key = binascii.a2b_hex(hmac_key)

    request_dict = dict(dict_object)
    request_dict['value'] = request_dict['amount']['value']
    request_dict['currency'] = request_dict['amount']['currency']

    element_orders = [
        'pspReference',
        'originalReference',
        'merchantAccountCode',
        'merchantReference',
        'value',
        'currency',
        'eventCode',
        'success',
    ]

    signing_string = ':'.join(map(str, (request_dict.get(element, '') for element in element_orders)))

    hm = hmac.new(hmac_key, signing_string.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(hm.digest())

def is_valid_hmac_notification(dict_object, hmac_key):
    dict_object = dict_object.copy()

    # check if notificationItems is in dict and dict_object to NotificationRequestItem
    if 'notificationItems' in dict_object:
        dict_object = dict_object['notificationItems'][0]['NotificationRequestItem']

    # check if additionalData is in dict_object
    if 'additionalData' not in dict_object:
        return False, "Missing additional data", ""

    # check if hmacSignature is not empty
    if dict_object['additionalData']['hmacSignature'] == "":
        return False, "Must Provide hmacSignature in additionalData", ""

    expected_sign = dict_object['additionalData']['hmacSignature']
    del dict_object['additionalData']
    merchant_sign = generate_notification_sig(dict_object, hmac_key)
    merchant_sign_str = merchant_sign.decode("utf-8")
    valid_signature = hmac.compare_digest(merchant_sign_str, expected_sign)

    if not valid_signature:
        # print('HMAC is invalid: {} {}'.format(expected_sign, merchant_sign_str))
        return False, expected_sign, merchant_sign_str

    return True, expected_sign, merchant_sign_str
