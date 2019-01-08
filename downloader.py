import os
import asyncio
import argparse

import uvloop
import requests
import flickrapi
import webbrowser


parser = argparse.ArgumentParser(description="""
    Fast Flickr Downloader just can download all you recent photos.
    You should have API key. See https://www.flickr.com/services/api/
    for details.
    """
)
parser.add_argument('--user-id', dest='user_id', required=True, help='User ID.')
parser.add_argument('--api-key', dest='api_key', required=True, help='Your API key.')
parser.add_argument('--api-secret', dest='api_secret', required=True, help='Your API secret.')
parser.add_argument('--page', dest='page', type=int, required=True, help='Start page.')
args = parser.parse_args()

api_key = args.api_key
api_secret = args.api_secret
USER_ID = args.user_id
PAGE = args.page
perms = "read"

flickr = flickrapi.FlickrAPI(api_key, api_secret, format='parsed-json')
if not flickr.token_valid(perms='read'):
    # Get a request token
    flickr.get_request_token(oauth_callback='oob')

    # Open a browser at the authentication URL. Do this however
    # you want, as long as the user visits that URL.
    authorize_url = flickr.auth_url(perms='read')
    webbrowser.open_new_tab(authorize_url)

    # Get the verifier code from the user. Do this however you
    # want, as long as the user gives the application the code.
    verifier = str(input('Verifier code: '))

    # Trade the request token for an access token
    flickr.get_access_token(verifier)


# sets = flickr.photosets.getList(user_id=USER_ID)
# print(sets['photosets']['photoset'][0])

def get_photos(page):
    photos = flickr.photos.search(
        user_id=USER_ID, per_page='20', sort='date-posted-desc',
        privacy_filter=5, page=page
    )
    return photos['photos']['photo']


def get_sizes(photo_id):
    return flickr.photos.getSizes(photo_id=photo_id)


async def run_sync_code(func, *args):
   loop = asyncio.get_event_loop()
   res = await loop.run_in_executor(None, func, *args)
   return res


async def store_photo(photo, name=None):
    photo_id = photo['id']
    sizes = await run_sync_code(get_sizes, photo_id)
    url = ''
    for s in sizes['sizes']['size']:
        if s['label'] == 'Original':
            url = s['source']
            break
    filename = os.path.join(args.user_id, url.split('/')[-1])
    filename_bak = '{}.bak'.format(filename)
    if not os.path.exists(filename):
        print(name, url, 'download...')
        response = await run_sync_code(requests.get, url)
        with open(filename_bak, 'wb') as f:
            f.write(response.content)
        os.rename(filename_bak, filename)
        print(name, url, 'download ok')
    else:
        print(name, url, 'already exists')


async def main():
    if not os.path.exists(args.user_id):
        os.mkdir(args.user_id)
    page = PAGE
    while page:
        print('Page', page)
        photos = await run_sync_code(get_photos, page)
        tasks = []
        for photo in photos:
            tasks.append(store_photo(photo))
        await asyncio.gather(*tasks)
        page += 1


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print('\nPlease wait...')
