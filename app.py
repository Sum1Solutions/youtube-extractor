from googleapiclient.discovery import build
from datetime import datetime
import json
import os
from dotenv import load_dotenv

def parse_youtube_date(date_str):
    """
    Parse YouTube date string handling both formats with and without microseconds
    """
    try:
        # Try parsing with microseconds
        return datetime.strptime(date_str.split('.')[0] + 'Z', '%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        # Try parsing without microseconds
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')

def get_channel_id(youtube, channel_url):
    """
    Get channel ID using different methods until successful.
    """
    channel_username = channel_url.split('@')[1]
    
    # Method 1: Try direct username lookup
    try:
        response = youtube.channels().list(
            part='id',
            forUsername=channel_username
        ).execute()
        
        if response.get('items'):
            return response['items'][0]['id']
    except Exception:
        pass
    
    # Method 2: Try channel search
    try:
        response = youtube.search().list(
            part='snippet',
            q=channel_username,
            type='channel',
            maxResults=1
        ).execute()
        
        if response.get('items'):
            return response['items'][0]['snippet']['channelId']
    except Exception:
        pass
    
    raise ValueError(f"Could not find channel ID for {channel_url}")

def get_channel_info(youtube, channel_id):
    """
    Get detailed channel information
    """
    response = youtube.channels().list(
        part='snippet,statistics,contentDetails',
        id=channel_id
    ).execute()
    
    if not response.get('items'):
        raise ValueError("Could not fetch channel information")
        
    channel_data = response['items'][0]
    return {
        'title': channel_data['snippet']['title'],
        'description': channel_data['snippet']['description'],
        'customUrl': channel_data['snippet'].get('customUrl', 'N/A'),
        'publishedAt': channel_data['snippet']['publishedAt'],
        'viewCount': channel_data['statistics']['viewCount'],
        'subscriberCount': channel_data['statistics']['subscriberCount'],
        'videoCount': channel_data['statistics']['videoCount'],
        'country': channel_data['snippet'].get('country', 'N/A')
    }

def get_channel_videos():
    """
    Fetch all videos from a YouTube channel and save their details to a text file.
    Uses environment variables for configuration.
    """
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment variables
    API_KEY = os.getenv('YOUTUBE_API_KEY')
    CHANNEL_URL = os.getenv('YOUTUBE_CHANNEL_URL')
    
    if not API_KEY or not CHANNEL_URL:
        raise ValueError("Missing required environment variables. Please check your .env file.")
    
    # Extract channel username from URL
    channel_username = CHANNEL_URL.split('@')[1]
    
    # Create YouTube API client
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    
    # Get channel ID using improved method
    channel_id = get_channel_id(youtube, CHANNEL_URL)
    print(f"Found channel ID: {channel_id}")
    
    # Get channel information
    channel_info = get_channel_info(youtube, channel_id)
    print(f"Fetched channel info for: {channel_info['title']}")
    
    # Get playlist ID for channel uploads
    playlist_response = youtube.channels().list(
        part='contentDetails',
        id=channel_id
    ).execute()
    
    if not playlist_response.get('items'):
        raise ValueError(f"Could not find upload playlist for channel {channel_username}")
    
    playlist_id = playlist_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    print(f"Found uploads playlist ID: {playlist_id}")
    
    # Fetch all video details
    videos = []
    next_page_token = None
    
    while True:
        try:
            playlist_items = youtube.playlistItems().list(
                part='snippet',
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()
            
            for item in playlist_items['items']:
                video_id = item['snippet']['resourceId']['videoId']
                video_data = {
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'publishedAt': item['snippet']['publishedAt'],
                    'videoId': video_id,
                    'url': f'https://www.youtube.com/watch?v={video_id}'
                }
                videos.append(video_data)
                print(f"Found video: {video_data['title']}")
            
            next_page_token = playlist_items.get('nextPageToken')
            if not next_page_token:
                break
                
        except Exception as e:
            print(f"Error fetching playlist items: {str(e)}")
            break
    
    if not videos:
        print("No videos found for this channel")
        return 0
    
    # Create output directory if it doesn't exist
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    
    # Save to text file
    output_file = os.path.join(output_dir, f'{channel_username}_videos.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write channel information
        f.write(f"Channel Information: {channel_info['title']}\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Channel URL: {CHANNEL_URL}\n")
        f.write(f"Created: {parse_youtube_date(channel_info['publishedAt']).strftime('%B %d, %Y')}\n")
        f.write(f"Subscribers: {int(channel_info['subscriberCount']):,}\n")
        f.write(f"Total Views: {int(channel_info['viewCount']):,}\n")
        f.write(f"Total Videos: {int(channel_info['videoCount']):,}\n")
        f.write(f"Country: {channel_info['country']}\n\n")
        f.write("Channel Description:\n")
        f.write(f"{channel_info['description']}\n\n")
        
        # Separator between channel info and videos
        f.write("=" * 50 + "\n")
        f.write("Videos\n")
        f.write("=" * 50 + "\n\n")
        
        # Write video information
        for video in videos:
            formatted_date = parse_youtube_date(video['publishedAt']).strftime('%B %d, %Y')
            
            f.write(f"Title: {video['title']}\n")
            f.write(f"Posted: {formatted_date}\n")
            f.write(f"URL: {video['url']}\n")
            f.write(f"Description:\n{video['description']}\n")
            f.write("-" * 50 + "\n\n")
    
    return len(videos)

if __name__ == "__main__":
    try:
        video_count = get_channel_videos()
        if video_count > 0:
            print(f"\nSuccessfully saved information for {video_count} videos.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")