import streamlit as st
import requests
import re
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Viral Topic Finder", layout="wide")

# !!! API KEY HARDCODED !!!
API_KEY = "AIzaSyDjTun06qZ6n4Ud84zZes71IgoJWYlD19o"

# Streamlit App Title
st.title("YouTube Viral Topics Finder 🚀")
st.markdown("Find trending videos on small channels based on specific keywords.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Search Settings")

# 1. Days Input (Duration)
days = st.sidebar.number_input("Look back (days):", min_value=1, max_value=365, value=7)

# 2. Subscriber Limit Input
max_subs_limit = st.sidebar.number_input(
    "Max Subscriber Count (Filter):", 
    min_value=0, 
    value=3000, 
    step=500, 
    help="Only show videos from channels with fewer subscribers than this."
)

# 3. Minimum Views Input
min_views_limit = st.sidebar.number_input(
    "Minimum Views (Filter):",
    min_value=0,
    value=2000,
    step=1000,
    help="Only show videos that have at least this many views."
)

st.sidebar.markdown("---")
st.sidebar.subheader("Video Duration Settings")

# 4. Custom Shorts Threshold
shorts_threshold = st.sidebar.number_input(
    "Define Shorts Length (seconds):",
    min_value=10,
    max_value=300,
    value=60,
    step=5,
    help="Videos shorter than or equal to this will be considered 'Shorts'."
)

# 5. Video Type Filter
video_type = st.sidebar.radio(
    "Filter by Type:",
    ("All", "Long Form", "Shorts")
)

# 6. Keywords Input
st.sidebar.markdown("---")
st.subheader("Enter Keywords")
st.markdown("Enter your topics below. Separate by Comma (`,`) or New Line.")
keyword_input = st.text_area(
    "Keywords:", 
    height=150,
    placeholder="Example:\nDigital Marketing,\nAffiliate Marketing,\nEarn Money Online"
)

# --- HELPER FUNCTIONS ---

def get_keywords_list(raw_input):
    if not raw_input:
        return []
    items = raw_input.replace("\n", ",").split(",")
    return [item.strip() for item in items if item.strip()]

def parse_duration(duration_str):
    if not duration_str: return 0
    match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration_str)
    if not match: return 0
    hours = int(match.group(1)[:-1]) if match.group(1) else 0
    minutes = int(match.group(2)[:-1]) if match.group(2) else 0
    seconds = int(match.group(3)[:-1]) if match.group(3) else 0
    return (hours * 3600) + (minutes * 60) + seconds

def calculate_time_ago(iso_date_str):
    """
    Calculates how much time has passed since the ISO date string.
    Returns strings like '2 days ago', '3 years ago'.
    """
    if not iso_date_str:
        return "Unknown"
    
    # Parse ISO format (Handles 'Z' correctly)
    try:
        published_date = datetime.strptime(iso_date_str, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        # Fallback if format is slightly different
        return "Unknown"

    now = datetime.utcnow()
    diff = now - published_date

    days = diff.days
    seconds = diff.seconds

    if days >= 365:
        years = days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif days >= 30:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif days > 0:
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif seconds >= 3600:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        return "Just now"

# --- MAIN LOGIC ---

keywords = get_keywords_list(keyword_input)

if st.button("Find Viral Videos"):
    if not keywords:
        st.warning("Please enter at least one keyword.")
    else:
        try:
            # Constants
            YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
            YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
            YOUTUBE_CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"
            
            # Calculate date range
            start_date = (datetime.utcnow() - timedelta(days=int(days))).isoformat("T") + "Z"
            
            results_found = False
            total_videos_found = 0

            st.write("---")
            st.info(f"Searching across {len(keywords)} keywords for the last {days} days...")

            # Progress bar
            progress_bar = st.progress(0)

            for idx, keyword in enumerate(keywords):
                # Update progress
                progress_bar.progress((idx + 1) / len(keywords))
                
                # Define search parameters
                search_params = {
                    "part": "snippet",
                    "q": keyword,
                    "type": "video",
                    "order": "viewCount",
                    "publishedAfter": start_date,
                    "maxResults": 30, 
                    "key": API_KEY,
                }

                # Fetch video data
                response = requests.get(YOUTUBE_SEARCH_URL, params=search_params)
                if response.status_code != 200:
                    st.error(f"API Error for '{keyword}': {response.json().get('error', {}).get('message', 'Unknown Error')}")
                    continue

                data = response.json()

                if "items" not in data or not data["items"]:
                    continue

                videos = data["items"]
                video_ids = []
                channel_ids = []

                for video in videos:
                    if "videoId" in video["id"]:
                        video_ids.append(video["id"]["videoId"])
                        channel_ids.append(video["snippet"]["channelId"])

                if not video_ids:
                    continue

                # Fetch video stats
                stats_params = {"part": "statistics,contentDetails,snippet", "id": ",".join(video_ids), "key": API_KEY}
                stats_response = requests.get(YOUTUBE_VIDEO_URL, params=stats_params)
                stats_data = stats_response.json()

                # Fetch channel stats (Added 'snippet' to get creation date)
                channel_params = {"part": "statistics,snippet", "id": ",".join(channel_ids), "key": API_KEY}
                channel_response = requests.get(YOUTUBE_CHANNEL_URL, params=channel_params)
                channel_data = channel_response.json()

                # Map data
                video_details_map = {item['id']: item for item in stats_data.get('items', [])}
                # Map channel stats AND snippet (for creation date)
                channel_map = {item['id']: item for item in channel_data.get('items', [])}

                keyword_results = []
                
                for video in videos:
                    vid_id = video['id']['videoId']
                    ch_id = video['snippet']['channelId']
                    
                    # Video Data
                    vid_details = video_details_map.get(vid_id, {})
                    vid_stats = vid_details.get('statistics', {})
                    vid_content = vid_details.get('contentDetails', {})
                    vid_snippet = vid_details.get('snippet', {}) # Need precise publish date
                    
                    views = int(vid_stats.get('viewCount', 0))
                    duration_iso = vid_content.get('duration', "PT0S")
                    duration_seconds = parse_duration(duration_iso)
                    video_publish_date = vid_snippet.get('publishedAt')
                    video_age_str = calculate_time_ago(video_publish_date)

                    # Channel Data
                    ch_data_item = channel_map.get(ch_id, {})
                    ch_stats = ch_data_item.get('statistics', {})
                    ch_snippet = ch_data_item.get('snippet', {})
                    
                    subs_raw = ch_stats.get('subscriberCount', 0)
                    subs = int(subs_raw) if subs_raw else 0 
                    
                    channel_publish_date = ch_snippet.get('publishedAt')
                    channel_age_str = calculate_time_ago(channel_publish_date)
                    
                    # --- FILTERS ---
                    if subs >= max_subs_limit or subs == 0: continue
                    if views < min_views_limit: continue

                    is_short = duration_seconds <= shorts_threshold
                    if video_type == "Shorts" and not is_short: continue
                    if video_type == "Long Form" and is_short: continue
                    
                    # Add to results
                    keyword_results.append({
                        "title": video["snippet"]["title"],
                        "desc": video["snippet"].get("description", "")[:150] + "...",
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                        "views": views,
                        "subs": subs,
                        "duration": f"{duration_seconds} sec",
                        "thumb": video["snippet"]["thumbnails"]["medium"]["url"],
                        "channel": video["snippet"]["channelTitle"],
                        "video_age": video_age_str,
                        "channel_age": channel_age_str
                    })

                # Display Results
                if keyword_results:
                    results_found = True
                    st.subheader(f"Results for: '{keyword}'")
                    
                    for res in keyword_results:
                        total_videos_found += 1
                        with st.container():
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.image(res["thumb"], use_container_width=True)
                            with col2:
                                st.markdown(f"### [{res['title']}]({res['url']})")
                                
                                # Row 1: Channel Info & Age
                                st.markdown(f"📺 **Channel:** {res['channel']} (Subs: `{res['subs']:,}`) | 🎂 **Channel Age:** `{res['channel_age']}`")
                                
                                # Row 2: Video Stats & Age
                                st.markdown(f"👁️ **Views:** `{res['views']:,}` | ⏳ **Duration:** `{res['duration']}` | 📅 **Uploaded:** `{res['video_age']}`")
                                
                                st.caption(res['desc'])
                            st.divider()

            if not results_found:
                st.warning("No videos found matching your criteria.")
            else:
                st.success(f"Search Complete! Total videos found: {total_videos_found}")

        except Exception as e:
            st.error(f"An error occurred: {e}")
