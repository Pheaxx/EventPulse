from cryptography.fernet import Fernet
from django.db import models
from django.conf import settings


class EncryptedField(models.TextField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        key = settings.ENCRYPTION_KEY.encode()
        f = Fernet(key)
        return f.decrypt(value.encode()).decode()

    def get_prep_value(self, value):
        if value is None:
            return value
        key = settings.ENCRYPTION_KEY.encode()
        f = Fernet(key)
        return f.encrypt(value.encode()).decode()