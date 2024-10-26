from googleapiclient.discovery import build
from datetime import datetime
import json
import os
from dotenv import load_dotenv

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
    
    # Get playlist ID for channel uploads
    playlist_response = youtube.channels().list(
        part='contentDetails',
        id=channel_id
    ).execute()
    
    if not playlist_response.get('items'):
        raise ValueError(f"Could not find upload playlist for channel {channel_username}")
    
    playlist_id = playlist_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    print(f"Found playlist ID: {playlist_id}")
    
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
                video_data = {
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'publishedAt': item['snippet']['publishedAt'],
                    'videoId': item['snippet']['resourceId']['videoId']
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
        f.write(f"Videos from {channel_username}\n")
        f.write("=" * 50 + "\n\n")
        
        for video in videos:
            # Convert UTC timestamp to readable format
            date = datetime.strptime(video['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')
            formatted_date = date.strftime('%B %d, %Y')
            
            f.write(f"Title: {video['title']}\n")
            f.write(f"Posted: {formatted_date}\n")
            f.write(f"Video ID: {video['videoId']}\n")
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