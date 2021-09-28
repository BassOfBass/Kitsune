from ..internals.database.database import get_raw_conn, return_conn, get_cursor
from datetime import datetime
def write_file_log(
    fhash: str,
    mtime: datetime,
    ctime: datetime,
    mime: str,
    ext: str,
    filename: str,
    service: str | None,
    user: str | None,
    post: str | None,
    inline: bool,
    remote_path: str,
    discord: bool = False,
    discord_message_server: str = '',
    discord_message_channel: str = '',
    discord_message_id: str = '',
):
    conn = get_raw_conn()

    cursor = conn.cursor()
    cursor.execute("INSERT INTO files (hash, mtime, ctime, mime, ext) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO UPDATE EXCLUDED.hash = hash RETURNING id", (fhash, mtime, ctime, mime, ext))
    file_id = cursor.fetchone()['id']

    if (discord):
        cursor = conn.cursor()
        cursor.execute("INSERT INTO file_discord_message_relationships (file_id, filename, server, channel, id) VALUES (%s, %s, %s, %s, %s)", (file_id, filename, discord_message_server, discord_message_channel, discord_message_id))
    else:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO file_post_relationships (file_id, filename, service, user, post, inline) VALUES (%s, %s, %s, %s, %s, %s)", (file_id, filename, service, user, post, inline))
    
    cursor = conn.cursor()
    cursor.execute("INSERT INTO file_server_relationships (file_id, remote_path) VALUES (%s, %s) RETURNING id", (file_id, remote_path))
    
    conn.commit()
    return_conn(conn)