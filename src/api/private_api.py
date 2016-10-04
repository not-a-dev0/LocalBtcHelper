# -*- coding: utf-8 -*-

import hmac
import hashlib
from datetime import datetime
from urllib import urlencode


from .public_api import PublicApi


class PrivateApi(PublicApi):

    def __init__(self, hmac_auth_key=None, hmac_auth_secret=None, debug=False):
        self.hmac_auth_key = hmac_auth_key
        self.hmac_auth_secret = hmac_auth_secret
        super(PrivateApi, self).__init__(debug)

    def send_request(self, endpoint, params, method, headers=None):
        params_encoded = ''
        if params != '':
            print(params)
            params_encoded = urlencode(params)
            if method == 'get':
                params_encoded = '?' + params_encoded

        now = datetime.utcnow()
        epoch = datetime.utcfromtimestamp(0)
        delta = now - epoch
        nonce = int(delta.total_seconds() * 1000)

        message = "{}{}{}{}".format(
            str(nonce),
            self.hmac_auth_key,
            endpoint,
            params_encoded
        )

        signature = hmac.new(
            self.hmac_auth_secret,
            msg=message,
            digestmod=hashlib.sha256)

        signature = signature.hexdigest().upper()

        headers = {
            'Apiauth-key': self.hmac_auth_key,
            'Apiauth-Nonce': str(nonce),
            'Apiauth-Signature': signature,
        }

        return super(PrivateApi, self). \
            send_request(endpoint, params, method, headers)
