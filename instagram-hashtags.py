#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import requests
import urllib.request
import urllib.parse
import urllib.error
import ssl
import json
import argparse
from pathlib import Path


class InstagramScraper:

    """
    - [v] Get JSON data for an hashtag
    - [v] Get all data for each post (edge_liked_by.count)
    - [v] Also get all users (followers count)
    """

    # Keep track of how many images we have
    # Keep track of the "after" cursor
    # Iterate until done or maxed out.

    max_items = 10000
    calls_per_hour = 200
    cursor = None

    """
    %7D }
    %7B {
    %22 "
    %3A :
    %2C ,
    %3D =
    """

    def get_data(self, variables, query_hash='174a5243287c5f3a7de741089750ab3b'):
        query = {
            'query_hash': query_hash,
            'variables': json.dumps(variables)
        }
        base = 'https://www.instagram.com/graphql/query/?'

        uri = base + urllib.parse.urlencode(query)
        res = urllib.request.urlopen(uri, context=self.ctx).read()
        return json.loads(res)

    def get_hashtag(self, hashtag, after=None):
        variables = {
            'tag_name': hashtag,
            'first': 12,
        }
        if after:
            variables['after'] = after

        return self.get_data(variables)

    def get_user_data(self, username, cache=False):
        print("Get user @%s." % (username))
        uri = "https://www.instagram.com/%s/?__a=1" % (username)
        # graphql.user.edge_followed_by is the follower count
        res = urllib.request.urlopen(uri, context=self.ctx).read()
        try:
            return json.loads(res)
        except:
            return None

    def get_user(self, user_id, cache=True):
        print("Get user #%s." % (user_id))
        filename = "data/users/user-%s.json" % (user_id)
        # @FIX Check that it doesn't exist already
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                item = json.load(f)
        else:
            username = self.get_username_by_user_id(user_id)
            item = self.get_user_data(username)
            if item:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(item, f, ensure_ascii=False, indent=4)

        return item

    def get_image(self, uri):
        pass

    def get_username_by_user_id(self, user_id):
        """
        If it's returning errors maybe the query hash needs to be updated.
        """
        variables = {
            'user_id': str(user_id),
            "include_highlight_reels": False,
            "include_reel": True,
            "include_chaining": False,
            "include_suggested_users": False,
            "include_logged_out_extras": False
        }

        data = self.get_data(
            variables, query_hash='aec5501414615eca36a9acf075655b1e')

        username = data['data']['user']['reel']['user']['username']

        return username

    def get_dataset(self, hashtags):
        # @TODO Load our items
        items = []
        for hashtag in hashtags:
            for filename in Path('data').glob("**/media-%s-*.json" % (hashtag)):
                with open(filename, 'rb') as f:
                    data = json.load(f)
                    items.extend(data)

        print("%d items" % (len(items)))
        # @TODO Score each item
        for i, node in enumerate(items):
            media_id = node['node']['id']
            user_id = node['node']['owner']['id']
            user = self.get_user(user_id)
            if not user:
                break
                # continue
            username = user['graphql']['user']['username']
            followers = user['graphql']['user']['edge_followed_by']['count']
            likes = node['node']['edge_liked_by']['count']

            print("Likes %d creator @%s followers %d." %
                  (likes, username, followers))

            # @TODO Calculate a class
            # @TODO Write out a result

        pass

    def get_images(self, hashtags):
        # Load the data json files relating to the hashtags.
        items = []
        min_size = 224

        for hashtag in hashtags:
            for filename in Path('data').glob("**/media-%s-*.json" % (hashtag)):
                with open(filename, 'rb') as f:
                    data = json.load(f)
                    items.extend(data)

        print("Downloading %d images for #%s." % (len(items), hashtags))

        for i, node in enumerate(items):
            image_id = node['node']['id']
            output_filename = "data/images/%s/%s/image-%s.jpg" % (
                hashtag, min_size, image_id)

            if os.path.exists(output_filename):
                print("%d%% Already retrieved image %s" %
                      (i*100/len(items), image_id))
            else:
                # Get the image > min_size
                for image in node['node']['thumbnail_resources']:
                    if image['config_width'] > min_size and image['config_height'] > min_size:
                        # download
                        print("%d%% Getting image %s liked %d times." %
                              (i*100/len(items), image_id, node['node']['edge_liked_by']['count']))
                        urllib.request.urlretrieve(
                            image['src'], output_filename)
                        break

    def get_creators(self, hashtags):
        """
        Requires get_username.
        """

        # Load the data json files relating to the hashtags.
        items = []
        for hashtag in hashtags:
            for filename in Path('data').glob("**/media-%s-*.json" % (hashtag)):
                with open(filename, 'rb') as f:
                    data = json.load(f)
                    items.extend(data)

        # @FIX Filter data on uniq users.
        # Iterate the filtered data looking for users.
        for i, node in enumerate(items):
            user_id = node['node']['owner']['id']
            output_filename = "data/users/user-%s.json" % (user_id)
            # @FIX Check that it doesn't exist already
            if os.path.exists(output_filename):
                print("%d%% Already retrieved user %s" %
                      (i*100/len(items), user_id))
            else:
                print("%d%% Getting user data for %s." %
                      (i*100/len(items), user_id))
                username = self.get_username_by_user_id(user_id)
                # Get user data
                item = self.get_user_data(username)
                if not item:
                    continue
                # print(item)
                # graphql.user.edge_followed_by
                print("User %s named \"%s\" has %s followers." % (
                    user_id, username, item['graphql']['user']['edge_followed_by']['count']))
                # Save a user file.
                with open(output_filename, 'w', encoding='utf-8') as f:
                    json.dump(item, f, ensure_ascii=False, indent=4)

    def get_media(self, hashtags):
        if not hashtags:
            with open('hashtag_list.txt') as f:
                data = f.readlines()
            hashtags = [x.strip() for x in data]

        max_times = 200/len(hashtags)

        for hashtag in hashtags:
            running = True
            after = None
            count = 0
            total = 0

            # Check if we already have files with an 'after'.
            list_of_files = Path('data').glob("**/media-%s-*.json" % (hashtag))

            latest_file = max(list_of_files, key=os.path.getctime)
            p, n = os.path.split(latest_file)
            t, h, a = n.split('-')
            after = a.replace('.json', '')
            print("Cursor is %s." % after)

            list_of_files = Path('data').glob("**/media-%s-*.json" % (hashtag))
            for filename in list_of_files:
                # Count the number of items so far.
                with open(filename, 'rb') as f:
                    data = json.load(f)
                    total += len(data)
                    print("%d%% Already have %d items." %
                          (total*100/self.max_items, total))

            while running:
                res = self.get_hashtag(hashtag, after)
                count += 1
                # print(res)

                # "edge_hashtag_to_media":
                # or "edge_hashtag_to_top_posts":
                data = res['data']['hashtag']['edge_hashtag_to_media']
                after = data['page_info']['end_cursor']
                self.cursor = after
                total += len(data['edges'])

                if data['page_info']['has_next_page']:
                    print("Fetching more #%s items." %
                          (hashtag))
                else:
                    print("Stopping (no more pages).")
                    running = False

                if total >= self.max_items:
                    print("Stopping (%d items retrieved)." % total)
                    running = False
                elif count >= max_times:
                    print("Rate limited (%d retrieved)." % count)
                    # Instead we could pause until the hour expires
                    running = False

                # Store the data
                items = data['edges']
                # Save the data
                # With the end_cursor as part of the name
                print("%d%% Saving %d #%s items" %
                      (total*100/self.max_items, len(items), hashtag))
                with open("data/media/media-%s-%s.json" % (hashtag, self.cursor), 'w',
                          encoding='utf-8') as f:
                    json.dump(items, f, ensure_ascii=False, indent=4)

    def main(self):
        parser = argparse.ArgumentParser(
            description='Generate labelled data set.')
        parser.add_argument('--stage', dest='stage',
                            choices=['media', 'creators', 'images', 'dataset'],
                            help='run the media data collection stage')
        parser.add_argument('--hashtags',
                            help='specify which hashtags to use')
        args = parser.parse_args()

        hashtags = None
        if args.hashtags:
            hashtags = args.hashtags.split(',')

        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

        if args.stage == 'media':
            self.get_media(hashtags)
        if args.stage == 'creators':
            self.get_creators(hashtags)
        if args.stage == 'images':
            self.get_images(hashtags)
        if args.stage == 'dataset':
            self.get_dataset(hashtags)


if __name__ == '__main__':
    obj = InstagramScraper()
    obj.main()
