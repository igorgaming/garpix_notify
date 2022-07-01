import os

from django.conf import settings
from django.utils.timezone import now

from twilio.rest import Client

from garpix_notify.models.config import NotifyConfig
from garpix_notify.models.choices import STATE
from garpix_notify.utils import ReceivingUsers

try:
    config = NotifyConfig.get_solo()
    IS_WHATS_APP_ENABLED = config.is_whatsapp_enabled
    WHATS_APP_AUTH_TOKEN = config.whatsapp_auth_token
    WHATS_APP_ACCOUNT_SID = config.whatsapp_account_sid
    WHATS_APP_NUMBER_SENDER = config.whats_app_sender
except Exception:
    IS_WHATS_APP_ENABLED = True
    WHATS_APP_AUTH_TOKEN = getattr(settings, 'WHATS_APP_AUTH_TOKEN', None)
    WHATS_APP_ACCOUNT_SID = getattr(settings, 'WHATS_APP_ACCOUNT_SID', None)
    WHATS_APP_NUMBER_SENDER = getattr(settings, 'WHATS_APP_NUMBER_SENDER', '')


class WhatsAppClient:

    def __init__(self, notify):
        self.notify = notify
        self.auth_token = WHATS_APP_AUTH_TOKEN
        self.account_sid = WHATS_APP_ACCOUNT_SID
        self.number_sender = WHATS_APP_NUMBER_SENDER

    def __send_message(self):
        if not IS_WHATS_APP_ENABLED:
            self.notify.state = STATE.DISABLED
            return
        client = Client(self.account_sid, self.auth_token)
        text_massage = self.notify.text
        users_list = self.notify.users_list.all()

        try:
            result = False
            if users_list.exists():
                participants = ReceivingUsers.run_receiving_users(users_list, value='phone')
                if participants:
                    for participant in participants:
                        result = client.messages.create(body=text_massage, from_=f'whatsapp:{self.number_sender}',
                                                        to=f'whatsapp:{participant}')
            else:
                result = client.messages.create(body=text_massage, from_=f'whatsapp:{self.number_sender}',
                                                to=f'whatsapp:{self.notify.phone}')
            if result:
                print(result.sid)
                self.notify.state = STATE.DELIVERED
                self.notify.sent_at = now()
            else:
                self.notify.state = STATE.REJECTED
                self.notify.to_log('REJECTED WITH DATA, please test it.')
        except Exception as e:  # noqa
            self.notify.state = STATE.REJECTED
            self.notify.to_log(str(e))

    @classmethod
    def send_whatsapp(cls, notify):
        cls(notify).__send_message()
