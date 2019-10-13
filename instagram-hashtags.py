#!/usr/bin/python
# -*- coding: utf-8 -*-
import requests
import urllib.request
import urllib.parse
import urllib.error
from bs4 import BeautifulSoup
import ssl
import json


class InstagramScraper:

    """
    - [ ] Get JSON data for an hashtag
    - [ ] Get all data for each post (edge_liked_by.count)
    - [ ] Also get all users (followers count)
    - [ ] Next page https://www.instagram.com/graphql/query/?query_hash=174a5243287c5f3a7de741089750ab3b&variables=%7B%22tag_name%22%3A%22bondibeach%22%2C%22first%22%3A12%2C%22after%22%3A%22QVFBTWhQUDRCeXdudTNVSnI0YXUtTWp0NG9BeFF5MEVmN21kajM2MnRaV3FaazQtZ3JRdVZpOXl1ekpqdFVoaFNoakxjRDVqNHRHZzZuSWJXR3Aycl9GdQ%3D%3D%22%7D
    """

    # Keep track of how many images we have
    # Keep track of the "after" cursor
    # Iterate until done or maxed out.

    max_items = 10000
    calls_per_hour = 200
    cursor = None

    def getlinks(self, hashtag, url):

        html = urllib.request.urlopen(url, context=self.ctx).read()
        soup = BeautifulSoup(html, 'html.parser')
        script = soup.find('script', text=lambda t:
                           t.startswith('window._sharedData'))
        page_json = script.text.split(' = ', 1)[1].rstrip(';')
        data = json.loads(page_json)

        print("Scraping %s grams with #%s." % (len(data), hashtag))
        for post in data['entry_data']['TagPage'][0]['graphql'
                                                     ]['hashtag']['edge_hashtag_to_media']['edges']:
            image_src = post['node']['thumbnail_resources'][1]['src']
            print(post['node']['id'])
            print(post['node']['edge_liked_by']['count'])
            print(post['node']['owner']['id'])
            hs = open(hashtag + '.txt', 'a')
            hs.write(image_src + '\n')
            hs.close()

    """
    https://www.instagram.com/graphql/query/?query_hash=174a5243287c5f3a7de741089750ab3b
    &variables=%7B%22tag_name%22%3A%22bondibeach%22%2C%22first%22%3A12%2C%22after%22%3A%22QVFBTWhQUDRCeXdudTNVSnI0YXUtTWp0NG9BeFF5MEVmN21kajM2MnRaV3FaazQtZ3JRdVZpOXl1ekpqdFVoaFNoakxjRDVqNHRHZzZuSWJXR3Aycl9GdQ%3D%3D%22%7D
    &variables={
        "tag_name":"bondibeach",
        "first":12,
        "after":"QVFBTWhQUDRCeXdudTNVSnI0YXUtTWp0NG9BeFF5MEVmN21kajM2MnRaV3FaazQtZ3JRdVZpOXl1ekpqdFVoaFNoakxjRDVqNHRHZzZuSWJXR3Aycl9GdQ=="}
    %7D }
    %7B {
    %22 "
    %3A :
    %2C ,
    %3D =
    """

    def get_hashtag(self, hashtag, after=None):
        variables = {
            'tag_name': hashtag,
            'first': 12,
        }
        if after:
            variables['after'] = after

        query = {
            'query_hash': '174a5243287c5f3a7de741089750ab3b',
            # 'variables': urllib.parse.quote_plus(json.dumps(variables))
            'variables': json.dumps(variables)
        }
        base = 'https://www.instagram.com/graphql/query/?'

        uri = base + urllib.parse.urlencode(query)
        # print(uri)

        res = urllib.request.urlopen(uri, context=self.ctx).read()
        return json.loads(res)

    def get_owner(self, owner):
        pass

    def get_image(self, uri):
        pass

    def get_hashtags(self):
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

        with open('hashtag_list.txt') as f:
            self.content = f.readlines()
        self.content = [x.strip() for x in self.content]

        max_times = 200/len(self.content)

        for hashtag in self.content:
            running = True
            after = None
            items = []
            count = 0

            while running:
                res = self.get_hashtag(hashtag, after)
                count += 1
                # print(res)

                # "edge_hashtag_to_media":
                # or "edge_hashtag_to_top_posts":
                data = res['data']['hashtag']['edge_hashtag_to_media']

                # Store the data
                items.extend(data['edges'])

                if data['page_info']['has_next_page']:
                    after = data['page_info']['end_cursor']
                    self.cursor = after
                    print("Getting more #%s (%d so far)" %
                          (hashtag, len(items)))
                else:
                    print("Stopping (no more pages).")
                    running = False

                if len(items) >= self.max_items:
                    print("Stopping (%d items retrieved)." % len(items))
                    running = False
                elif count >= max_times:
                    print("Rate limited (%d retrieved)." % count)
                    # Instead we could pause until the hour expires
                    running = False

            # Save the data
            print("Saving")
            # Alternatively we could save every run as a separate file
            # With the end_cursor as part of the name
            with open("data-%s-%s.json" % (hashtag, self.cursor), 'w', encoding='utf-8') as f:
                json.dump(items, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    obj = InstagramScraper()
    obj.main()
