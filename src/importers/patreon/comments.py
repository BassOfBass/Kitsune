import config
import requests
from datetime import datetime
from src.internals.database.database import get_raw_conn, return_conn
from src.internals.utils.logger import log
from src.internals.utils.proxy import get_proxy
from src.internals.utils.scrapper import create_scrapper_session
from src.lib.artist import delete_comment_cache_keys
from src.lib.post import get_comments_for_posts
from .api import comments_request


def import_comments(url, key, post_id, user_id, import_id):  # noqa C901
    scraper_data = comments_request(url, key, import_id)

    if not scraper_data:
        return

    all_comments = get_comments_for_posts('patreon', post_id)

    while True:
        for comment in scraper_data['data']:
            comment_id = comment['id']
            commenter_id = comment['relationships']['commenter']['data']['id']
            try:
                if list(filter(lambda comment: comment['id'] == post_id and comment['commenter'] == commenter_id, all_comments)):
                    log(import_id,
                        f"Skipping comment {comment_id} from post {post_id} because already exists", to_client=False)
                    continue
                import_comment(comment, user_id, import_id)
            except Exception:
                log(import_id, f"Error while importing comment {comment_id} from post {post_id}", 'exception', True)
                continue

        if scraper_data.get('included'):
            for included in scraper_data['included']:
                if (included['type'] == 'comment'):
                    comment_id = comment['id']
                    commenter_id = comment['relationships']['commenter']['data']['id']
                    try:
                        if list(filter(lambda comment: comment['id'] == post_id and comment['commenter'] == commenter_id, all_comments)):
                            log(import_id,
                                f"Skipping comment {comment_id} from post {post_id} because already exists", to_client=False)
                            continue
                        import_comment(included, user_id, import_id)
                    except Exception:
                        log(import_id,
                            f"Error while importing comment {comment_id} from post {post_id}", 'exception', True)
                        continue

        if 'links' in scraper_data and 'next' in scraper_data['links']:
            log(import_id, f"Processing next page of comments for post {post_id}", to_client=False)
            try:
                scraper = create_scrapper_session().get(scraper_data['links']['next'], cookies={
                    'session_id': key}, proxies=get_proxy())
                scraper_data = scraper.json()
                scraper.raise_for_status()
            except requests.HTTPError as e:
                log(import_id, f"Status code {e.response.status_code} when contacting Patreon API.", 'exception')
                return
            except Exception:
                log(import_id, 'Error connecting to cloudscraper. Please try again.', 'exception')
                return
        else:
            return


def import_comment(comment, user_id, import_id):
    post_id = comment['relationships']['post']['data']['id']
    commenter_id = comment['relationships']['commenter']['data']['id']
    comment_id = comment['id']

    if (comment['attributes']['deleted_at']):
        log(import_id, f"Skipping comment {comment_id} from post {post_id} because it is deleted", to_client=False)
        return

    log(import_id, f"Starting comment import: {comment_id} from post {post_id}", to_client=False)

    post_model = {
        'id': comment_id,
        'post_id': post_id,
        'parent_id': comment['relationships']['parent']['data']['id'] if comment['relationships']['parent']['data'] else None,
        'commenter': commenter_id,
        'service': 'patreon',
        'content': comment['attributes']['body'],
        'added': datetime.now(),
        'published': comment['attributes']['created'],
    }

    columns = post_model.keys()
    data = ['%s'] * len(post_model.values())
    query = """
        INSERT INTO comments
            ({fields})
        VALUES
            ({values})
        ON CONFLICT DO NOTHING
    """.format(
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
        requests.request(
            'BAN', f"{config.ban_url}/{post_model['service']}/user/" + user_id + '/post/' + post_model['post_id'])
    delete_comment_cache_keys(post_model['service'], user_id, post_model['post_id'])
