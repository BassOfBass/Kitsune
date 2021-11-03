from typing import Dict
from urllib.parse import urlparse
from retry import retry
from websocket import create_connection
import requests
from src.internals.cache.redis import delete_keys
from src.internals.utils.logger import log
from src.internals.utils.proxy import get_proxy
from src.internals.utils.scrapper import create_scrapper_session
from src.lib.autoimport import kill_key
from .urls import sendbird_token_url


def posts_request(url, key, import_id, key_id, **request_options):
    try:
        posts: Dict = patreon_request(url, key, **request_options)
        return posts
    except requests.HTTPError as e:
        log(import_id, f"Status code {e.response.status_code} when contacting Patreon API.", 'exception')
        if (e.response.status_code == 401):
            delete_keys([f'imports:{import_id}'])
            if (key_id):
                kill_key(key_id)
        return
    except Exception:
        log(import_id, 'Error connecting to cloudscraper. Please try again.', 'exception')
        return


def dms_request(url, key, import_id, **request_options):
    try:
        dms: Dict = patreon_request(url, key, **request_options)
        return dms
    except requests.HTTPError as e:
        log(import_id, f"Status code {e.response.status_code} when contacting Patreon message campaign API.", 'exception')
        return
    except Exception:
        log(import_id, 'Error connecting to cloudscraper. Please try again.', 'exception')
        return


def comments_request(url: str, key: str, import_id: str, **request_options):
    try:
        comments: Dict = patreon_request(url, key, **request_options)
        return comments
    except requests.HTTPError as e:
        log(import_id, f"Status code {e.response.status_code} when contacting Patreon API.", 'exception')
        return
    except Exception:
        log(import_id, 'Error connecting to cloudscraper. Please try again.', 'exception')
        return


def patreon_request(url: str, key: str, **request_options):
    """
    The base request for Patreon API.
    """
    scraper = create_scrapper_session()
    response = scraper.get(url, cookies={'session_id': key}, proxies=get_proxy(), **request_options)
    scraper_data: Dict = response.json()
    response.raise_for_status()
    return scraper_data


@retry(tries=10, delay=2)
def get_ws_connection(url):
    proxy = get_proxy()
    if (proxy):
        proxy_url = urlparse(proxy['https'])
        return create_connection(
            url,
            http_proxy_host=proxy_url.hostname,
            http_proxy_port=proxy_url.port,
            http_proxy_auth=(proxy_url.username,
                             proxy_url.password) if proxy_url.username and proxy_url.password else None,
            proxy_type=proxy_url.scheme
        )
    else:
        return create_connection(url)


def get_sendbird_token(key, import_id):
    try:
        scraper = create_scrapper_session().get(sendbird_token_url, cookies={'session_id': key}, proxies=get_proxy())
        scraper_data = scraper.json()
        scraper.raise_for_status()
    except requests.HTTPError as e:
        log(import_id, f"Status code {e.response.status_code} when contacting Patreon Sendbird token API.", 'exception')
        raise
    except Exception:
        log(import_id, 'Error connecting to cloudscraper. Please try again.', 'exception')
        raise

    return scraper_data['session_token']
