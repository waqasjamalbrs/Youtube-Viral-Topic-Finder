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

# 3. Video Type Filter (Shorts vs Long)
video_type = st.sidebar.radio(
    "Video Type:",
    ("All", "Long Form (> 1 min)", "Shorts (< 1 min)")
)

# 4. Keywords Input
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
    # Replace newlines with commas, then split by comma
    items = raw_input.replace("\n", ",").split(",")
    # Strip whitespace and remove empty strings
    return [item.strip() for item in items if item.strip()]

def parse_duration(duration_str):
    """
    Parses YouTube ISO 8601 duration (e.g., PT1H2M10S) into total seconds.
    """
    if not duration_str:
        return 0
    
    # Regex to extract hours, minutes, seconds
    match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration_str)
    if not match:
        return 0

    hours = int(match.group(1)[:-1]) if match.group(1) else 0
    minutes = int(match.group(2)[:-1]) if match.group(2) else 0
    seconds = int(match.group(3)[:-1]) if match.group(3) else 0

    total_seconds = (hours * 3600) + (minutes * 60) + seconds
    return total_seconds

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
                    "maxResults": 20, # Fetch more to allow for filtering
                    "key": API_KEY,
                }

                # Fetch video data
                response = requests.get(YOUTUBE_SEARCH_URL, params=search_params)
                
                if response.status_code != 200:
                    error_msg = response.json().get('error', {}).get('message', 'Unknown Error')
                    st.error(f"API Error for '{keyword}': {error_msg}")
                    continue

                data = response.json()

                if "items" not in data or not data["items"]:
                    continue

                videos = data["items"]
                video_ids = []
                channel_ids = []

                # Collect IDs
                for video in videos:
                    if "videoId" in video["id"]:
                        video_ids.append(video["id"]["videoId"])
                        channel_ids.append(video["snippet"]["channelId"])

                if not video_ids:
                    continue

                # Fetch video statistics AND contentDetails (for duration)
                stats_params = {
                    "part": "statistics,contentDetails", 
                    "id": ",".join(video_ids), 
                    "key": API_KEY
                }
                stats_response = requests.get(YOUTUBE_VIDEO_URL, params=stats_params)
                stats_data = stats_response.json()

                # Fetch channel statistics (for subscriber count)
                channel_params = {"part": "statistics", "id": ",".join(channel_ids), "key": API_KEY}
                channel_response = requests.get(YOUTUBE_CHANNEL_URL, params=channel_params)
                channel_data = channel_response.json()

                # Map data for easy access
                video_details_map = {item['id']: item for item in stats_data.get('items', [])}
                channel_stats_map = {item['id']: item['statistics'] for item in channel_data.get('items', [])}

                # Process and Filter
                keyword_results = []
                
                for video in videos:
                    vid_id = video['id']['videoId']
                    ch_id = video['snippet']['channelId']
                    
                    # Get details
                    vid_details = video_details_map.get(vid_id, {})
                    vid_stats = vid_details.get('statistics', {})
                    vid_content = vid_details.get('contentDetails', {})
                    
                    views = int(vid_stats.get('viewCount', 0))
                    duration_iso = vid_content.get('duration', "PT0S")
                    duration_seconds = parse_duration(duration_iso)

                    # Get channel subs
                    subs_raw = channel_stats_map.get(ch_id, {}).get('subscriberCount', 0)
                    subs = int(subs_raw) if subs_raw else 0 
                    
                    # --- FILTERS ---
                    
                    # 1. Subscriber Filter
                    if subs >= max_subs_limit or subs == 0:
                        continue
                        
                    # 2. Video Type Filter (Shorts vs Long)
                    is_short = duration_seconds <= 60
                    
                    if video_type == "Shorts (< 1 min)" and not is_short:
                        continue
                    if video_type == "Long Form (> 1 min)" and is_short:
                        continue
                    
                    # If passed all filters, add to results
                    keyword_results.append({
                        "title": video["snippet"]["title"],
                        "desc": video["snippet"].get("description", "")[:150] + "...",
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                        "views": views,
                        "subs": subs,
                        "duration": f"{duration_seconds} sec",
                        "thumb": video["snippet"]["thumbnails"]["medium"]["url"],
                        "channel": video["snippet"]["channelTitle"]
                    })

                # Display Results for this keyword
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
                                st.markdown(f"**[{res['title']}]({res['url']})**")
                                st.write(f"📺 **Channel:** {res['channel']}")
                                st.markdown(f"👁️ **Views:** `{res['views']:,}` | 👥 **Subs:** `{res['subs']:,}` | ⏳ **Duration:** `{res['duration']}`")
                                st.caption(res['desc'])
                            st.divider()

            if not results_found:
                st.warning("No videos found matching your criteria. Try changing the duration, filters, or keywords.")
            else:
                st.success(f"Search Complete! Total videos found: {total_videos_found}")

        except Exception as e:
            st.error(f"An error occurred: {e}")
