from typing import List
from urllib.parse import urlencode

base_url = 'https://www.patreon.com'
base_params = {
    'json-api-version': '1.0'
}
sendbird_token_url = f'{base_url}/api/sendbird_session_token?json-api-version=1.0'


def posts_url(campaign_id: str):
    url = f'{base_url}/api/posts'
    params = {
        'include': ','.join([
            'user',
            'attachments',
            'campaign,poll.choices',
            'poll.current_user_responses.user',
            'poll.current_user_responses.choice',
            'poll.current_user_responses.poll',
            'access_rules.tier.null',
            'images.null',
            'audio.null'
        ]),
        'fields[post]': ','.join([
            'change_visibility_at',
            'comment_count',
            'content',
            'current_user_can_delete',
            'current_user_can_view',
            'current_user_has_liked',
            'embed',
            'image',
            'is_paid',
            'like_count',
            'min_cents_pledged_to_view',
            'post_file',
            'post_metadata',
            'published_at',
            'patron_count',
            'patreon_url',
            'post_type',
            'pledge_url',
            'thumbnail_url',
            'teaser_text',
            'title',
            'upgrade_url',
            'url',
            'was_posted_by_campaign_owner',
            'edited_at'
        ]),
        'fields[user]': ','.join([
            'image_url',
            'full_name',
            'url'
        ]),
        'fields[campaign]': ','.join([
            'show_audio_post_download_links',
            'avatar_photo_url',
            'earnings_visibility',
            'is_nsfw',
            'is_monthly',
            'name',
            'url'
        ]),
        'fields[access_rule]': ','.join([
            'access_rule_type',
            'amount_cents'
        ]),
        'fields[media]': ','.join([
            'id',
            'image_urls',
            'download_url',
            'metadata',
            'file_name',
            'state'
        ]),
        'sort': '-published_at',
        'filter[is_draft]': 'false',
        'filter[contains_exclusive_posts]': 'true',
        'json-api-use-default-includes': 'false',
        'json-api-version': '1.0',
        'filter[campaign_id]': campaign_id
    }
    query = urlencode(params)
    final_url = f'{url}?{query}'

    return final_url


def campaign_list_url():
    path = '/api/pledges'
    params = {
        'include': ','.join([
            'address',
            'campaign',
            'reward.items',
            'most_recent_pledge_charge_txn',
            'reward.items.reward_item_configuration',
            'reward.items.merch_custom_variants',
            'reward.items.merch_custom_variants.item',
            'reward.items.merch_custom_variants.merch_product_variant'
        ]),
        'fields[address]': ','.join([
            'id',
            'addressee',
            'line_1',
            'line_2',
            'city',
            'state',
            'postal_code',
            'country',
            'phone_number'
        ]),
        'fields[campaign]': ','.join([
            'avatar_photo_url',
            'cover_photo_url',
            'is_monthly',
            'is_non_profit',
            'name',
            'pay_per_name',
            'pledge_url',
            'published_at',
            'url'
        ]),
        'fields[user]': ','.join([
            'thumb_url',
            'url',
            'full_name'
        ]),
        'fields[pledge]': ','.join([
            'amount_cents',
            'currency',
            'pledge_cap_cents',
            'cadence',
            'created_at',
            'has_shipping_address',
            'is_paused',
            'status'
        ]),
        'fields[reward]': ','.join([
            'description',
            'requires_shipping',
            'unpublished_at'
        ]),
        'fields[reward-item]': ','.join([
            'id',
            'title',
            'description',
            'requires_shipping',
            'item_type',
            'is_published',
            'is_ended',
            'ended_at',
            'reward_item_configuration'
        ]),
        'fields[merch-custom-variant]': ','.join([
            'id',
            'item_id'
        ]),
        'fields[merch-product-variant]': ','.join([
            'id',
            'color',
            'size_code'
        ]),
        'fields[txn]': ','.join([
            'succeeded_at',
            'failed_at'
        ]),
        'json-api-use-default-includes': 'false',
        'json-api-version': '1.0'
    }
    query = urlencode(params)
    final_url = f'{base_url}{path}?{query}'
    return final_url


def bills_url(year: str):
    """
    We fetch the same fields as the patreon site itself to not trigger any possible protections.
    User card data is actually not saved or accessed.
    """
    path = '/api/bills'
    params = {
        'timezone': 'UTC',
        'include': ','.join([
            'post.campaign.null',
            'campaign.null',
            'card.null'
        ]),
        'fields[campaign]': ','.join([
            'avatar_photo_url',
            'currency',
            'cover_photo_url',
            'is_monthly',
            'is_non_profit',
            'is_nsfw',
            'name',
            'pay_per_name',
            'pledge_url',
            'url'
        ]),
        'fields[post]': ','.join([
            'title',
            'is_automated_monthly_charge',
            'published_at',
            'thumbnail',
            'url',
            'pledge_url'
        ]),
        'fields[bill]': ','.join([
            'status',
            'amount_cents',
            'created_at',
            'due_date',
            'vat_charge_amount_cents',
            'vat_country',
            'monthly_payment_basis',
            'patron_fee_cents',
            'is_non_profit',
            'bill_type',
            'currency',
            'cadence',
            'taxable_amount_cents'
        ]),
        'fields[patronage_purchase]': ','.join([
            'amount_cents',
            'currency',
            'created_at',
            'due_date',
            'vat_charge_amount_cents',
            'vat_country',
            'status',
            'cadence',
            'taxable_amount_cents'
        ]),
        'fields[card]': ','.join([
            'number',
            'expiration_date',
            'card_type',
            'merchant_name',
            'needs_sfw_auth',
            'needs_nsfw_auth'
        ]),
        'json-api-use-default-includes': 'false',
        'json-api-version': '1.0',
        'filter[due_date_year]': year
    }
    query = urlencode(params)
    final_url = f'{base_url}{path}?{query}'
    return final_url


def comments_url(post_id: str):
    path = f'/api/posts/{post_id}/comments'
    params = {
        'include': ','.join([
            'commenter.campaign.null',
            'commenter.flairs.campaign',
            'parent',
            'post',
            'first_reply.commenter.campaign.null',
            'first_reply.parent',
            'first_reply.post',
            'exclude_replies',
            'on_behalf_of_campaign.null',
            'first_reply.on_behalf_of_campaign.null'
        ]),
        'fields[comment]': ','.join([
            'body',
            'created',
            'deleted_at',
            'is_by_patron',
            'is_by_creator',
            'vote_sum',
            'current_user_vote',
            'reply_count',
        ]),
        'fields[post]': ','.join([
            'comment_count'
        ]),
        'fields[user]': ','.join([
            'image_url',
            'full_name',
            'url'
        ]),
        'fields[flair]': ','.join([
            'image_tiny_url',
            'name'
        ]),
        'page[count]': '10',
        'sort': '-created',
        'json-api-use-default-includes': 'false',
        'json-api-version': '1.0',
    }
    query = urlencode(params)
    final_url = f'{base_url}{path}?{query}'
    return final_url


def sendbird_ws_url(current_user_id: str, sendbird_token: str, timestamp: int):
    base_url = 'wss://ws-beaa7a4b-1278-4d71-98fa-a76a9882791e.sendbird.com/'
    params = {
        'p': 'JS',
        'sv': '3.0.127',
        'ai': 'BEAA7A4B-1278-4D71-98FA-A76A9882791E',
        'user_id': current_user_id,
        'access_token': sendbird_token,
        'active': '1',
        'SB-User-Agent': 'JS%2Fc3.0.127%2F%2F',
        'Request-Sent-Timestamp': timestamp,
        'include_extra_data': ','.join([
            'premium_feature_list',
            'file_upload_size_limit',
            'emoji_hash'
        ])
    }
    query = urlencode(params)
    final_url = f'{base_url}?{query}'
    return final_url


def sendbird_messages_url(url: str, timestamp: str = '9007199254740991'):
    base_url = 'https://api-beaa7a4b-1278-4d71-98fa-a76a9882791e.sendbird.com'
    path = '/v3/group_channels/{url}/messages'
    params = {
        'is_sdk': 'true',
        'prev_limit': '15',
        'next_limit': '0',
        'include': 'false',
        'reverse': 'false',
        'message_t': timestamp,
        'with_sorted_meta_array': 'false',
        'include_reactions': 'false',
        'include_thread_info': 'false',
        'include_replies': 'false',
        'include_parent_message_text': 'false'
    }
    query = urlencode(params)
    final_url = f'{base_url}{path}?{query}'
    return final_url


def sendbird_channels_url(current_user: str, token: str, campaigns: List[str]):
    base_url = 'https://api-beaa7a4b-1278-4d71-98fa-a76a9882791e.sendbird.com'
    path = f'/v3/users/{current_user}/my_group_channels'
    params = {
        'token': token,
        'limit': '15',
        'order': 'latest_last_message',
        'show_member': 'true',
        'show_read_receipt': 'true',
        'show_delivery_receipt': 'true',
        'show_empty': 'true',
        'member_state_filter': 'joined_only',
        'custom_types': ','.join(campaigns),
        'super_mode': 'all',
        'public_mode': 'all',
        'unread_filter': 'all',
        'hidden_mode': 'unhidden_only',
        'show_frozen': 'true'
    }
    query = urlencode(params)
    final_url = f'{base_url}{path}?{query}'
    return final_url


def current_user_url():
    path = '/api/current_user'
    params = {
        'include': 'campaign.null',
        'fields[user]': ','.join([
            'full_name',
            'image_url'
        ]),
        'fields[campaign]': ','.join([
            'name',
            'avatar_photo_url'
        ]),
        'json-api-version': '1.0'
    }
    query = urlencode(params)
    final_url = f'{base_url}{path}?{query}'
    return final_url


def members_url(current_user_id: str):
    path = '/api/members'
    params = {
        'filter[user_id]': current_user_id,
        'filter[can_be_messaged]': 'true',
        'include': 'campaign.creator.null',
        'fields[member]': '[]',
        'fields[campaign]': ','.join([
            'avatar_photo_url',
            'name',
            'url'
        ]),
        'page[count]': '500',
        'json-api-use-default-includes': 'false',
        'json-api-version': '1.0'
    }
    query = urlencode(params)
    final_url = f'{base_url}{path}?{query}'
    return final_url


def current_user_url_with_pledges():
    path = '/api/current_user'
    params = {
        'include': ','.join([
            'pledges.creator.campaign.null',
            'pledges.campaign.null',
            'follows.followed.campaign.null'
        ]),
        'fields[user]': ','.join([
            'image_url',
            'full_name',
            'url',
            'social_connections'
        ]),
        'fields[campaign]': ','.join([
            'avatar_photo_url',
            'creation_name',
            'pay_per_name',
            'is_monthly',
            'is_nsfw',
            'name'
            'url'
        ]),
        'fields[pledge]': ','.join([
            'amount_cents',
            'cadence'
        ]),
        'fields[follow]': '[]',
        'json-api-version': '1.0'
    }
    query = urlencode(params)
    final_url = f'{base_url}{path}?{query}'
    return final_url
