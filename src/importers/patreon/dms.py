import time
import json
from .api import dms_request, get_ws_connection, get_sendbird_token
from .urls import members_url, sendbird_ws_url
from .posts import get_current_user_id, import_channels


def get_dm_campaigns(key, current_user_id, import_id):
    url = members_url(current_user_id)
    campaigns_data = dms_request(url, key, import_id)

    if not campaigns_data:
        return

    return set(campaign['relationships']['campaign']['data']['id'] for campaign in campaigns_data['data'])


def import_dms(key, import_id, contributor_id):
    current_user_id = get_current_user_id(key, import_id)
    sendbird_token = get_sendbird_token(key, import_id)
    timestamp = round(time.time() * 1000)
    ws_url = sendbird_ws_url(current_user_id, sendbird_token, timestamp)
    ws = get_ws_connection(ws_url)
    ws_data = json.loads(ws.recv().replace('LOGI', ''))
    ws.close()

    import_channels(ws_data['key'], current_user_id, get_dm_campaigns(
        key, current_user_id, import_id), import_id, contributor_id)
