import requests
import urllib.parse
import os
from dotenv import load_dotenv

import assets.constants

class Bibliothek:
    def __init__(self):
        self.session = requests.Session()

        self.session.headers = {
            'accept': 'application/vnd.api+json',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'de',
            'content-type': 'text/html; charset=utf-8',
            'origin': 'https://anny.eu',
            'referer': 'https://anny.eu/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0'
        }

    def login(self):
        load_dotenv()
        username = os.getenv('USERNAME')
        password = os.getenv('PASSWORD')
        login = KIT(username, password)

        self.session.headers['authorization'] = ("Bearer " + TOKEN).encode('utf-8')

    def get_intervals(self, ressource_id, date):

        r = self.session.get(
            'https://b.anny.eu/api/v1/intervals/start',
            params={
                'date': date,
                'service_id[449]': 1,
                'ressource_id': ressource_id,
                'timezone': assets.constants.TIMEZONE
            }
        )
        return r.json()

    def calculate_all_available_slots(self, ressource_id, date):

        slot_list = self.get_intervals(ressource_id, date)

        for slot in slot_list:
            message = slot['start_date'] + " - " + str(slot['number_available'])
            print(message)

    def get_children(self, ressource = '1-lehrbuchsammlung-eg-und-1-og'):

        r = self.session.get(
            'https://b.anny.eu/api/v1/resources/' + ressource + '/children',
            params={
                'page[number]': 1,
                'page[size]': 1000,
                'filter[available_from]': '2025-07-10T00:00:00+02:00',
                # 'filter[availability_exact_match]': 0,
                'filter[exclude_hidden]': 0,
                'filter[exclude_child_resources]': 0,
                'filter[availability_service_id]': 449,
                'filter[include_unavailable]': 1,
                'sort': 'name',
            }
        )

        return r.json()


if __name__ == '__main__':
    bibliothek = Bibliothek()
    print(bibliothek.get_children())
