"""YouTube to Webhook
This script connects to the YouTube API and gets video info.
This info gets filtered and embedded then sent off to a webhook.
End result, any time there is a new video posted, it autmoatically posts it to a discord channel.

    Returns:
        _type_: _description_
"""
import json
import os
import asyncio
import aiohttp
import isodate

import yt_config

# Configuration Section
LAST_VIDEO_FILE = './last_video_id.json'
MIN_VIDEO_DURATION = 60

# This is for testing, move to config befre use.


# Sessions to get json
async def get_json(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
        
# posting embed to webhook
async def post_to_webhook(data: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(yt_config.DISCORD_WEBHOOK_URL, json=data) as response:
            if response.status == 204:
                print ("Posted to Discord successfully!")
            else:
                print(f"Failed to post to Discord:{response.status}")

# Gets latest video from YouTube API.
async def get_latest_video():
    url = (
        f'https://www.googleapis.com/youtube/v3/search?'
        f'key={yt_config.YOUTUBE_API_KEY}&channelId={yt_config.CHANNEL_ID}&part=snippet,id&order=date&maxResults=1'
    )
    return await get_json(url)

# Gets more details about video, like length.
async def get_video_details(video_id):
    url = (
        f'https://www.googleapis.com/youtube/v3/videos?'
        f'key={yt_config.YOUTUBE_API_KEY}&id={video_id}&part=contentDetails'
    )
    return await get_json(url)

# Embed for Discord.
async def post_to_discord(video_info):
    embed = {
        "title": video_info['title'],
        "url": f"https://www.youtube.com/watch?v={video_info['id']}",
        "description": video_info['description'],
        "color": 16711680,
        "footer": {
            "text": "Just dropped a new video!"
        },
        "image": {
            "url": video_info['thumbnail_url']
        }
    }
    data = {
        "embeds":[embed]
    }
    await post_to_webhook(data)

async def load_last_video_id():
    if os.path.exists(LAST_VIDEO_FILE):
        with open(LAST_VIDEO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get('video_id')

async def save_last_video_id(video_id):
    with open(LAST_VIDEO_FILE, 'w', encoding='utf-8') as f:
        json.dump({'video_id': video_id}, f)

async def main():
    latest_video = await get_latest_video()
    
    # if empty, return
    if not latest_video:
        return
    
    # if it doesn't contain the items key, catch and return 
    try:
        latest_video_items = latest_video["items"]
    except KeyError:
        return
    
    # if we're here we know we have a latest video with an items parameter.
    video_id = latest_video_items[0]['id']['videoId']
    video_title = latest_video_items[0]['snippet']['title']
    video_description = latest_video_items[0]['snippet']['description']
    thumbnail_url = latest_video_items[0]['snippet']['thumbnails']['default']['url']

    # Get video details to check duration
    try:
        video_details_items = await get_video_details(video_id)
        video_details_items = video_details_items['items']
    except KeyError:
        return

    duration = video_details_items[0]['contentDetails']['duration']
    print(f"Video Duration: {duration}")

    # Check if the video is a normal video and not a short, has a duration longer than 60s.
    if (len(video_id) == 11 and
            'shorts' not in latest_video
            ['items'][0]['snippet']['thumbnails']['default']['url']):
        # Convert ISO 8601 duration to seconds
        duration_seconds = isodate.parse_duration(duration).total_seconds()
        if duration_seconds > MIN_VIDEO_DURATION:
            last_video_id = await load_last_video_id()

            if video_id != last_video_id:
                print(f"New video found: {video_title}")
                await post_to_discord({
                    'id': video_id,
                    'title': video_title,
                    'description': video_description,
                    'thumbnail_url': thumbnail_url
                })
                await save_last_video_id(video_id)
            else:
                print("No new video found.")
        else:
            print("The video is shorter than 60 seconds, skipping...")
    else:
        print("The latest video is a short, skipping...")

if __name__ == '__main__':
    asyncio.run(main())
