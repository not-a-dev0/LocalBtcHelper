# -*- coding: utf-8 -*-
import os
from src.api.localbitcoins_api import LocalBitcoinsApi
import shelve


DEFAULT_KEY = \
    'd7441f99f41e3297b786dd279474abf6'
DEFAULT_SECRET = \
    '21049bfe9cedcd4dd07a0ccb76e72ef4b50768be21ff02f4543caadd9e90d413'

PERSISTENT_STORAGE_INITIAL = 'shelve_initial.txt'
PERSISTENT_STORAGE_AWAITING = 'shelve_awaiting.txt'


class TradingHelper(object):
    OUR_NAME = 'nexchange.ru'

    def __init__(self, localbitcoins_api):
        self.bit = localbitcoins_api
        self.storage_contacts_initial = \
            shelve.open(PERSISTENT_STORAGE_INITIAL)
        self.storage_contacts_awaiting = \
            shelve.open(PERSISTENT_STORAGE_AWAITING)

    def check_messages(self):
        bit = LocalBitcoinsApi(key, sec, True)
        dashboard = bit.get_dashboard()
        contacts = dashboard['contact_list']
        active_contact_ids = [str(x['data']['contact_id']) for
                              x in contacts]

        for index, contact_id in enumerate(active_contact_ids):
            contact_id = str(contact_id)
            if not self.storage_contacts_initial.has_key(contact_id):
                self.say_hello(contact_id)
                self.offer_payment_methods(contact_id)
                self.storage_contacts_initial[contact_id] = True
                self.storage_contacts_initial.sync()

            messages = bit.get_contact_messages(contact_id)
            client_messages = [msg for msg in messages['message_list']
                               if TradingHelper.OUR_NAME not in msg['sender']['name']]
            if not self.storage_contacts_awaiting.has_key(contact_id) \
                    and len(client_messages):
                bank_message = self.determine_bank_msg(client_messages)
                if len(bank_message):
                    self.bit.post_message_to_contact(contact_id, bank_message)
                    self.storage_contacts_awaiting[contact_id] = True

        self.clean_old_contacts(active_contact_ids)
        self.storage_contacts_initial.close()
        self.storage_contacts_awaiting.close()

    def clean_old_contacts(self, active_contact_ids):
        old_contacts = [contact_id for contact_id in self.storage_contacts_initial
                        if contact_id not in active_contact_ids]
        for contact_id in old_contacts:
            if self.storage_contacts_initial.has_key(contact_id):
                del self.storage_contacts_initial[contact_id]
            if self.storage_contacts_awaiting.has_key(contact_id):
                del self.storage_contacts_awaiting[contact_id]
                self.spam_after_deal(contact_id)
                self.leave_feedback(contact_id)

    def say_hello(self, contact_id):
        msg = 'Доброго времени суток, \n \
               спасибо что Вы выбрали Nexchange! \n'
        self.bit.post_message_to_contact(contact_id, msg)

    def offer_payment_methods(self, contact_id):
        msg = 'как Вам будет удобно оплатить \
               (сбер,альфа, райф или другой банк)?'

        self.bit.post_message_to_contact(contact_id, msg)

    def leave_feedback(self, contact_id):
        # TODO: add feedback
        pass

    def determine_bank_msg(self, messages):
        def escape(txt):
            try:
                escaped = repr(txt.encode('utf-8'))
            except UnicodeDecodeError:
                escaped = txt

            return escaped.upper()

        def tokenize(msg):
            output = []
            for index, sequence in enumerate(tokens):
                for token in sequence:
                    if token.decode('utf-8').upper() in msg['msg'].upper() \
                            and not msg['is_admin']:
                        output.append(responses[index])

            return output

        suffix = ' Инициалы: О. Б.'
        tokens = [
            ['sber', 'Сбер', 'cber', 'sbr', 'Сбр'],
            ['alfa', 'Альфа', 'Алфа', 'alpha'],
            ['raif', 'Райф']
        ]

        responses = [
            'Сбербанк: 4274 2780 0964 3456',
            'Алфа-банк: 5521 7520 5438 2960',
            'Райффайзен:  5100 7050 0115 5912'
        ]

        final_output = []

        for msg in messages:
            final_output += tokenize(msg)
        final_output = list(set(final_output))
        return '\n'.join(final_output) + suffix \
            if len(final_output) else []

    def spam_after_deal(self, contact_id):
        msg = 'Спасибо за обращение. \n \
               Не забудьте оставить положительный отзыв и посетите наш сайт и офис в МСК'
        self.bit.post_message_to_contact(contact_id, msg)


if __name__ == '__main__':
    key = os.getenv('LOCALBTC_KEY', DEFAULT_KEY)
    sec = os.getenv('LOCALBTC_KEY', DEFAULT_SECRET)
    debug = False
    local_bit = LocalBitcoinsApi(key, sec, debug)
    helper = TradingHelper(local_bit)
    helper.check_messages()
