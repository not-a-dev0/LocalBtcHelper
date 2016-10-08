# -*- coding: utf-8 -*-
from src.api.localbitcoins_api import LocalBitcoinsApi
from twilio.rest import TwilioRestClient
from twilio.exceptions import TwilioException
from src.settings.base import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, \
    TWILIO_PHONE_FROM
import shelve

PERSISTENT_STORAGE_INITIAL = 'shelve_initial_{}_{}.txt'
PERSISTENT_STORAGE_AWAITING = 'shelve_awaiting_{}_{}.txt'
NEW_CONTACT_TEMPLATE = 'New contact! \nAccount: {} is {} {} BTC FOR {}'
NEW_DISPUTE_TEMPLATE = '!!!Dispute!!! \nAccount: {}  is {} {} BTC FOR {}'


class TradingHelper(object):
    BUY = 'buy'
    SELL = 'sell'
    CONTACT_ID = 'contact_id'
    IS_DISPUTE = 'disputed_at'
    IS_BUYING = 'is_buying'

    def __init__(self, account, subscribed_phones, name):
        self.name = name
        self.subscribed_phones = subscribed_phones
        self.bit = account
        self.contacts = [{}]

        # BUY storage
        self.storage_contacts_initial_buy = \
            shelve.open(PERSISTENT_STORAGE_INITIAL.format(TradingHelper.BUY, self.name))
        self.storage_contacts_awaiting_sell = \
            shelve.open(PERSISTENT_STORAGE_AWAITING.format(TradingHelper.BUY, self.name))

        # SELL storage
        self.storage_contacts_initial_sell = \
            shelve.open(PERSISTENT_STORAGE_INITIAL.format(TradingHelper.SELL, self.name))

    def check_messages(self):
        dashboard = self.bit.get_dashboard()
        self.contacts = dashboard['contact_list']
        if not self.contacts:
            print({"message": "No contacts, Exiting"})
            return
        for contact_index, contact in enumerate(self.contacts):
            contact_id = str(contact['data'][TradingHelper.CONTACT_ID])
            trad_type = TradingHelper.BUY if contact['data'][TradingHelper.IS_BUYING] \
                else TradingHelper.SELL
            is_disputed = contact['data'][TradingHelper.IS_DISPUTE]
            if trad_type == TradingHelper.SELL:
                self.handle_sell(contact, contact_id, is_disputed)
            else:
                self.handle_buy(contact, contact_id, is_disputed)

    def handle_buy(self, contact, contact_id, is_disputed):
        if not self.storage_contacts_initial_sell.has_key(contact_id):
            self.send_sms(contact, is_disputed)
            if not is_disputed:
                self.say_hello(contact)
                self.storage_contacts_initial_buy[contact_id] = True
                self.storage_contacts_initial_buy.sync()

        self.clean_old_contacts()

    def handle_sell(self, contact, contact_id, is_disputed):
        if not self.storage_contacts_initial_sell.has_key(contact_id):
            self.send_sms(contact, is_disputed)
            if not is_disputed:
                self.say_hello(contact_id)
                self.offer_payment_methods(contact_id)
                self.storage_contacts_initial_sell[contact_id] = True
                self.storage_contacts_initial_sell.sync()

        messages = self.bit.get_contact_messages(contact_id)
        client_messages = [msg for msg in messages['message_list']
                           if self.name not in msg['sender']['name']]
        if not self.storage_contacts_awaiting_sell.has_key(contact_id) \
                and client_messages:
            bank_message = self.determine_bank_msg(client_messages)
            if len(bank_message):
                self.bit.post_message_to_contact(contact_id, bank_message)
                self.storage_contacts_awaiting_sell[contact_id] = True

        self.clean_old_contacts()
        self.storage_contacts_initial_buy.close()
        self.storage_contacts_awaiting_sell.close()

    def send_sms(self, contact, is_dispute):
        if contact['data']['is_buying']:
            key = 'seller'
            action = 'SELLING'
        else:
            key = 'buyer'
            action = 'BUYING'

        template = NEW_DISPUTE_TEMPLATE if is_dispute \
            else NEW_CONTACT_TEMPLATE
        msg = template.format(
            contact['data'][key]['username'],
            action,
            contact['data']['amount_btc'],
            contact['data']['amount']
        )

        errors = []
        messages = []
        for phone in self.subscribed_phones:
            try:
                client = TwilioRestClient(
                    TWILIO_ACCOUNT_SID,
                    TWILIO_AUTH_TOKEN)
                message = client.messages.create(
                    body=msg, to=phone, from_=TWILIO_PHONE_FROM)
                messages.append(message)
            except TwilioException as err:
                errors.append(err)
        return errors, messages

    def clean_old_contacts(self):
        active_contact_ids = [c['data'][TradingHelper.CONTACT_ID] for c in self.contacts]
        old_contacts = [contact_id for contact_id in self.storage_contacts_initial_buy
                        if contact_id not in active_contact_ids]
        for contact_id in old_contacts:
            if self.storage_contacts_initial_buy.has_key(contact_id):
                del self.storage_contacts_initial_buy[contact_id]

            if self.storage_contacts_initial_sell.has_key(contact_id):
                del self.storage_contacts_initial_sell[contact_id]

            if self.storage_contacts_awaiting_sell.has_key(contact_id):
                del self.storage_contacts_awaiting_sell[contact_id]
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

    def determine_bank_msg(self, contact):
        def tokenize(msg):
            output = []
            for index, sequence in enumerate(tokens):
                for token in sequence:
                    if token.decode('utf-8').upper() in msg['msg'].upper() \
                            and not msg['is_admin']:
                        output.append(responses[index])

            return output

        suffix = '\n Инициалы: О. Б. \n назначение платежа: {} (важно!)'
        tokens = [
            ['sber', 'Сбер', 'cber', 'sbr', 'Сбр'],
            ['alfa', 'Альфа', 'Алфа', 'alpha', 'Альфы', 'Алфы'],
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
    accounts = [
        {
            'name': 'nexchange.ru',
            'secret': '00c1d059d00862dd1815419adf515f7c340efb4743d0e88dd4948a59664f5081',
            'key': 'a969c2abe1d778ff145421251307f667',
            'subscribed_phones': [
                '+79254497306',
                '+79153077459'
            ]
        },
        {
            'name': 'Nexchange',
            'secret': '0467413b4aa66b2a1dd48f04cd7523dd6611685c3968b190a0598e335345943b',
            'key': 'e46f5e105915bfd665dd22287d5467b0',
            'subscribed_phones': [
                '+79254497306',
                '+79153077459'
            ]
        }
    ]

    for index, account in enumerate(accounts):
        api = LocalBitcoinsApi(account['key'], account['secret'])

        debug = False

        helper = TradingHelper(api, account['subscribed_phones'],
                               account['name'])
        helper.check_messages()
