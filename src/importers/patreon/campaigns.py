import json
import os
import sys
import uuid
from datetime import datetime
from urllib.parse import urlparse

import config
import requests
from dateutil.parser import parse as parse_date
from gallery_dl import text
from src.internals.utils.download import download_file
from src.internals.utils.logger import log
from src.internals.utils.proxy import get_proxy
from src.internals.utils.scrapper import create_scrapper_session

from src.internals.database.database import get_raw_conn, return_conn
from src.lib.artist import (delete_artist_cache_keys,
                            get_all_artist_flagged_post_ids,
                            get_all_artist_post_ids, get_all_dnp,
                            update_artist)
from src.lib.autoimport import encrypt_and_save_session_for_auto_import
from src.lib.post import delete_post_flags

from .api import posts_request
from .comments import import_comments
from .urls import bills_url, campaign_list_url, comments_url

sys.setrecursionlimit(100000)


def get_campaign_ids(key, import_id):
    active_campaign_ids = get_active_campaign_ids(key, import_id)
    cancelled_campaign_ids = get_cancelled_campaign_ids(key, import_id)

    campaign_ids = set()

    if active_campaign_ids:
        campaign_ids.update(active_campaign_ids)

    if cancelled_campaign_ids:
        campaign_ids.update(cancelled_campaign_ids)

    return list(campaign_ids)


def get_active_campaign_ids(key, import_id):
    """Get ids of campaigns with active pledge"""
    try:
        scraper = create_scrapper_session().get(campaign_list_url(), cookies={'session_id': key}, proxies=get_proxy())
        scraper_data = scraper.json()
        scraper.raise_for_status()
    except requests.HTTPError as e:
        log(import_id, f"Status code {e.response.status_code} when contacting Patreon API.", 'exception')
        return set()
    except Exception:
        log(import_id, 'Error connecting to cloudscraper. Please try again.', 'exception')
        return set()

    campaign_ids = set()
    for pledge in scraper_data['data']:
        try:
            campaign_id = pledge['relationships']['campaign']['data']['id']
            campaign_ids.add(campaign_id)
        except Exception:
            log(import_id, f"Error while retieving campaign id for pledge {pledge['id']}", 'exception', True)
            continue

    return campaign_ids


def get_cancelled_campaign_ids(key, import_id):  # noqa C901
    """
    Retrieve ids of campaigns for which pledge has been cancelled
    but they've been paid for in this or previous month
    """
    today_date = datetime.today()
    bill_data = []
    current_year = str(today_date.year)
    try:
        scraper = create_scrapper_session().get(
            bills_url(current_year),
            cookies={'session_id': key},
            proxies=get_proxy()
        )
        scraper_data = scraper.json()
        scraper.raise_for_status()

        bill_data.extend(scraper_data['data'])

        # get data for previous year as well if today's date is less or equal to january 7th
        if today_date.month == 1 and today_date.day <= 7:
            previous_year = str(today_date.year - 1)
            scraper = create_scrapper_session().get(
                bills_url(previous_year),
                cookies={'session_id': key},
                proxies=get_proxy()
            )
            scraper_data = scraper.json()
            scraper.raise_for_status()

            if scraper_data.get('data'):
                bill_data.extend(scraper_data['data'])
    except requests.HTTPError as exc:
        log(import_id, f"Status code {exc.response.status_code} when contacting Patreon API.", 'exception')
        return set()
    except Exception:
        log(import_id, 'Error connecting to cloudscraper. Please try again.', 'exception')
        return set()

    bills = []
    for bill in bill_data:
        try:
            if bill['attributes']['status'] != 'successful':
                continue

            due_date = parse_date(bill['attributes']['due_date'])

            # We check all bills for the current month as well as bills from the previous month
            # for the first 7 days of the current month because posts are still available
            # for some time after cancelling membership
            if due_date.month == today_date.month or ((due_date.month == today_date.month - 1 or (due_date.month == 12 and today_date.month == 1)) and today_date.day <= 7):
                bills.append(bill)
        except Exception:
            log(import_id, "Error while parsing one of the bills", 'exception', True)
            continue

    campaign_ids = set()

    if len(bills) > 0:
        for bill in bills:
            try:
                campaign_id = bill['relationships']['campaign']['data']['id']
                if not campaign_id in campaign_ids:  # noqa E713
                    campaign_ids.add(campaign_id)
            except Exception:
                log(import_id, "Error while retrieving one of the cancelled campaign ids", 'exception', True)
                continue

    return campaign_ids


def import_campaign_page(url, key, import_id, contributor_id=None, allowed_to_auto_import=None, key_id=None):  # noqa C901
    scraper_data = posts_request(url, key, import_id, key_id)

    if not scraper_data:
        return

    if (allowed_to_auto_import):
        try:
            encrypt_and_save_session_for_auto_import('patreon', key, contributor_id=contributor_id)
            log(import_id, "Your key was successfully enrolled in auto-import!", to_client=True)
        except:
            log(import_id, "An error occured while saving your key for auto-import.", 'exception')

    dnp = get_all_dnp()
    post_ids_of_users = {}
    flagged_post_ids_of_users = {}
    while True:
        for post in scraper_data['data']:
            try:
                user_id = post['relationships']['user']['data']['id']
                post_id = post['id']

                if list(filter(lambda artist: artist['id'] == user_id and artist['service'] == 'patreon', dnp)):
                    log(import_id, f"Skipping user {user_id} because they are in do not post list", to_client=True)
                    return

                if not post['attributes']['current_user_can_view']:
                    log(import_id,
                        f'Skipping {post_id} from user {user_id} because this post is not available for current subscription tier', to_client=True)
                    continue

                import_comments(comments_url(post_id), key, post_id, user_id, import_id)

                # existence checking
                if not post_ids_of_users.get(user_id):
                    post_ids_of_users[user_id] = get_all_artist_post_ids('patreon', user_id)
                if not flagged_post_ids_of_users.get(user_id):
                    flagged_post_ids_of_users[user_id] = get_all_artist_flagged_post_ids('patreon', user_id)
                if len(list(filter(lambda post: post['id'] == post_id, post_ids_of_users[user_id]))) > 0 and len(list(filter(lambda flag: flag['id'] == post_id, flagged_post_ids_of_users[user_id]))) == 0:
                    log(import_id,
                        f'Skipping post {post_id} from user {user_id} because already exists', to_client=True)
                    continue
                log(import_id, f"Starting import: {post_id} from user {user_id}")

                post_model = {
                    'id': post_id,
                    '"user"': user_id,
                    'service': 'patreon',
                    'title': post['attributes']['title'] or "",
                    'content': '',
                    'embed': {},
                    'shared_file': False,
                    'added': datetime.now(),
                    'published': post['attributes']['published_at'],
                    'edited': post['attributes']['edited_at'],
                    'file': {},
                    'attachments': []
                }

                if post['attributes']['content']:
                    post_model['content'] = post['attributes']['content']
                    for image in text.extract_iter(post['attributes']['content'], '<img data-media-id="', '>'):
                        download_url = text.extract(image, 'src="', '"')[0]
                        path = urlparse(download_url).path
                        ext = os.path.splitext(path)[1]
                        fn = str(uuid.uuid4()) + ext
                        _, hash_filename, _ = download_file(
                            download_url,
                            'patreon',
                            user_id,
                            post_id,
                            name=fn,
                            inline=True
                        )
                        post_model['content'] = post_model['content'].replace(download_url, hash_filename)

                if post['attributes']['embed']:
                    post_model['embed']['subject'] = post['attributes']['embed']['subject']
                    post_model['embed']['description'] = post['attributes']['embed']['description']
                    post_model['embed']['url'] = post['attributes']['embed']['url']

                if post['attributes']['post_file']:
                    reported_filename, hash_filename, _ = download_file(
                        post['attributes']['post_file']['url'],
                        'patreon',
                        user_id,
                        post_id,
                        name=post['attributes']['post_file']['name']
                    )
                    post_model['file']['name'] = reported_filename
                    post_model['file']['path'] = hash_filename

                for attachment in post['relationships']['attachments']['data']:
                    reported_filename, hash_filename, _ = download_file(
                        f"https://www.patreon.com/file?h={post_id}&i={attachment['id']}",
                        'patreon',
                        user_id,
                        post_id,
                        cookies={'session_id': key}
                    )
                    post_model['attachments'].append({
                        'name': reported_filename,
                        'path': hash_filename
                    })

                if post['relationships']['images']['data']:
                    for image in post['relationships']['images']['data']:
                        for media in list(filter(lambda included: included['id'] == image['id'], scraper_data['included'])):
                            if media['attributes']['state'] != 'ready':
                                continue
                            reported_filename, hash_filename, _ = download_file(
                                media['attributes']['download_url'],
                                'patreon',
                                user_id,
                                post_id,
                                name=media['attributes']['file_name']
                            )
                            post_model['attachments'].append({
                                'name': reported_filename,
                                'path': hash_filename
                            })

                if post['relationships']['audio']['data']:
                    for media in list(filter(lambda included: included['id'] == post['relationships']['audio']['data']['id'], scraper_data['included'])):
                        if media['attributes']['state'] != 'ready':
                            continue
                        reported_filename, hash_filename, _ = download_file(
                            media['attributes']['download_url'],
                            'patreon',
                            user_id,
                            post_id,
                            name=media['attributes']['file_name']
                        )
                        post_model['attachments'].append({
                            'name': reported_filename,
                            'path': hash_filename
                        })

                post_model['embed'] = json.dumps(post_model['embed'])
                post_model['file'] = json.dumps(post_model['file'])
                for i in range(len(post_model['attachments'])):
                    post_model['attachments'][i] = json.dumps(post_model['attachments'][i])

                columns = post_model.keys()
                data = ['%s'] * len(post_model.values())
                data[-1] = '%s::jsonb[]'  # attachments
                query = "INSERT INTO posts ({fields}) VALUES ({values}) ON CONFLICT (id, service) DO UPDATE SET {updates}".format(
                    fields=','.join(columns),
                    values=','.join(data),
                    updates=','.join([f'{column}=EXCLUDED.{column}' for column in columns])
                )
                conn = get_raw_conn()
                try:
                    cursor = conn.cursor()
                    cursor.execute(query, list(post_model.values()))
                    conn.commit()
                finally:
                    return_conn(conn)

                update_artist('patreon', user_id)
                delete_post_flags('patreon', user_id, post_id)

                if (config.ban_url):
                    requests.request('BAN', f"{config.ban_url}/{post_model['service']}/user/" + post_model['"user"'])
                delete_artist_cache_keys('patreon', user_id)

                log(import_id, f"Finished importing {post_id} from user {user_id}", to_client=False)
            except Exception:
                log(import_id, f"Error while importing {post_id} from user {user_id}", 'exception', True)
                continue

        if 'links' in scraper_data and 'next' in scraper_data['links']:
            log(import_id, 'Finished processing page. Processing next page.')
            try:
                scraper = create_scrapper_session().get(scraper_data['links']['next'], cookies={
                    'session_id': key}, proxies=get_proxy())
                scraper_data = scraper.json()
                scraper.raise_for_status()
            except requests.HTTPError as e:
                log(import_id, f"Status code {e.response.status_code} when contacting Patreon API.", 'exception')
                return
        else:
            log(import_id, "Finished scanning for posts.")
            return
