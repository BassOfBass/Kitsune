import json
from datetime import datetime

import config
import requests
from setproctitle import setthreadtitle
from src.internals.utils.logger import log
from src.internals.utils.proxy import get_proxy
from src.internals.utils.scrapper import create_scrapper_session

from src.internals.cache.redis import delete_keys
from src.internals.database.database import get_raw_conn, return_conn
from src.lib.artist import delete_dm_cache_keys, dm_exists

from .campaigns import get_campaign_ids, import_campaign_page
from .dms import import_dms
from .urls import (current_user_url, posts_url, sendbird_channels_url,
                   sendbird_messages_url)


def get_current_user_id(key, import_id):
    try:
        scraper = create_scrapper_session().get(current_user_url(), cookies={'session_id': key}, proxies=get_proxy())
        scraper_data = scraper.json()
        scraper.raise_for_status()
    except requests.HTTPError as e:
        log(import_id, f"Status code {e.response.status_code} when contacting Patreon current user API.", 'exception')
        raise
    except Exception:
        log(import_id, 'Error connecting to cloudscraper. Please try again.', 'exception')
        raise

    return scraper_data['data']['id']


def import_channel(auth_token, url, import_id, current_user, contributor_id, timestamp='9007199254740991'):
    try:
        scraper = create_scrapper_session(useCloudscraper=False).get(sendbird_messages_url(url, timestamp), headers={
            'session-key': auth_token,
            'referer': 'https://www.patreon.com/'
        }, proxies=get_proxy())
        scraper_data = scraper.json()
        scraper.raise_for_status()
    except requests.HTTPError as e:
        log(import_id, f"Status code {e.response.status_code} when contacting DM message API.", 'exception')
        raise

    for message in scraper_data['messages']:
        # https://sendbird.com/docs/chat/v3/platform-api/guides/messages
        dm_id = str(message['message_id'])
        user_id = message['user']['user_id']

        if (message['is_removed']):
            log(import_id, f"Skipping message {dm_id} from user {user_id} because already exists", to_client=False)
            continue

        log(import_id, f"Starting message import: {dm_id} from user {user_id}", to_client=False)

        if (message['type'] == 'MESG'):
            if dm_exists('patreon', user_id, dm_id, message['message']):
                log(import_id, f"Skipping message {dm_id} from user {user_id} because already exists", to_client=False)
                continue

            if user_id == current_user:
                log(import_id,
                    f"Skipping message {dm_id} from user {user_id} because it was made by the contributor", to_client=False)
                continue

            if not message['message'].strip():
                log(import_id, f"Skipping message {dm_id} from user {user_id} because it is empty", to_client=False)
                continue

            post_model = {
                'import_id': import_id,
                'contributor_id': contributor_id,
                'id': dm_id,
                '"user"': user_id,
                'service': 'patreon',
                'content': message['message'],
                'embed': {},  # Unused, but could populate with OpenGraph data in the future
                'added': datetime.now(),
                'published': datetime.fromtimestamp(message['created_at'] / 1000.0),
                'file': {}  # Unused. Might support file DMs if Patreon begins using them.
            }

            post_model['embed'] = json.dumps(post_model['embed'])
            post_model['file'] = json.dumps(post_model['file'])

            columns = post_model.keys()
            data = ['%s'] * len(post_model.values())
            query = "INSERT INTO unapproved_dms ({fields}) VALUES ({values}) ON CONFLICT DO NOTHING".format(
                fields=','.join(columns),
                values=','.join(data)
            )
            conn = get_raw_conn()
            try:
                cursor = conn.cursor()
                cursor.execute(query, list(post_model.values()))
                conn.commit()
            finally:
                return_conn(conn)

            if (config.ban_url):
                requests.request('BAN', f"{config.ban_url}/{post_model['service']}/user/" + user_id + "/dms")
            delete_dm_cache_keys(post_model['service'], user_id)
        elif (message['type'] == 'FILE'):
            log(import_id, f'Skipping message {dm_id} because file DMs are unsupported', to_client=True)
            continue

    if (scraper_data['messages']):
        import_channel(auth_token, url, import_id, current_user, contributor_id,
                       timestamp=scraper_data['messages'][0]['created_at'])


def import_channels(auth_token, current_user, campaigns, import_id, contributor_id, token=''):
    try:
        url = sendbird_channels_url(current_user, token, campaigns)
        scraper = create_scrapper_session(useCloudscraper=False).get(url, headers={
            'session-key': auth_token,
            'referer': 'https://www.patreon.com/'
        }, proxies=get_proxy())
        scraper_data = scraper.json()
        scraper.raise_for_status()
    except requests.HTTPError as e:
        log(import_id, f"Status code {e.response.status_code} when contacting DM channel list API.", 'exception')
        return

    for channel in scraper_data['channels']:
        try:
            import_channel(auth_token, channel['channel']['channel_url'], import_id, current_user, contributor_id)
        except Exception:
            log(import_id, f"Error while importing DM channel {channel['channel']['channel_url']}", 'exception', True)
            continue

    if (scraper_data['next']):
        import_channels(auth_token, current_user, campaigns, import_id, contributor_id, token=scraper_data['next'])


def import_posts(import_id, key, allowed_to_scrape_dms, contributor_id, allowed_to_auto_import, key_id):
    setthreadtitle(f'Kitsune Import|{import_id}')

    if (allowed_to_scrape_dms):
        log(import_id, "Importing DMs...", to_client=True)
        import_dms(key, import_id, contributor_id)
        log(import_id, "Done importing DMs.", to_client=True)

    campaign_ids = get_campaign_ids(key, import_id)

    if campaign_ids:
        for campaign_id in campaign_ids:
            log(import_id, f"Importing campaign {campaign_id}", to_client=True)
            import_campaign_page(
                posts_url(str(campaign_id)),
                key,
                import_id,
                contributor_id=contributor_id,
                allowed_to_auto_import=allowed_to_auto_import,
                key_id=key_id
            )

        log(import_id, "Finished scanning for posts.")
        delete_keys([f'imports:{import_id}'])
    else:
        delete_keys([f'imports:{import_id}'])
        log(import_id, "No active subscriptions or invalid key. No posts will be imported.", to_client=True)
