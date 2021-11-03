
import json
import sys
import time
import uuid
from os import makedirs
from os.path import join, splitext
from urllib.parse import urlparse

import config
import dateutil
import requests
from flask import current_app
from gallery_dl import text
from requests.adapters import HTTPAdapter
from retry import retry

from src.internals.utils.download import DownloaderException, download_file
from src.internals.utils.logger import log
from src.internals.utils.proxy import get_proxy
from src.internals.utils.scrapper import create_scrapper_session
from urllib3 import Retry
from websocket import create_connection
from datetime import datetime

from src.internals.cache.redis import delete_keys
from src.internals.database.database import get_conn, get_raw_conn, return_conn
from src.lib.artist import (delete_artist_cache_keys,
                            delete_comment_cache_keys, delete_dm_cache_keys,
                            dm_exists, get_all_artist_flagged_post_ids,
                            get_all_artist_post_ids, get_all_dnp,
                            index_artists, is_artist_dnp, update_artist)
from src.lib.autoimport import (encrypt_and_save_session_for_auto_import,
                                kill_key)
from src.lib.post import (comment_exists, delete_backup, delete_post_flags,
                          get_comments_for_posts, move_to_backup, post_exists,
                          post_flagged, restore_from_backup)

from .urls import posts_url, campaign_list_url, bills_url

sys.setrecursionlimit(100000)
