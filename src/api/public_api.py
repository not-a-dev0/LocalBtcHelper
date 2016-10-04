# -*- coding: utf-8 -*-

import json
import requests


class PublicApi(object):
    BASE_URL = 'https://localbitcoins.com'

    def __init__(self, debug=False):
        self.debug = debug

    def send_request(self, endpoint, params, method, headers=None):
        headers = headers if headers else {}
        if method == 'get':
            response = requests.get(PublicApi.BASE_URL + endpoint,
                                    headers=headers, params=params)
        else:
            response = requests.post(PublicApi.BASE_URL + endpoint,
                                     headers=headers, data=params)

        if self.debug:
            print('REQUEST: {}{}'.format(PublicApi.BASE_URL, endpoint))
            print('PARAMS: {}'.format(str(params)))
            print('METHOD: {}'.format(method))
            print('RESPONSE: {}'.format(response.text))

        try:
            return json.loads(response.text)['data']
        except KeyError:
            # TODO: add logging blyat
            pass
