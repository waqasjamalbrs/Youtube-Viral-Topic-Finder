import streamlit as st
import requests
import re
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Viral Topic Finder", layout="wide")

# --- SECURE API KEY HANDLING ---
# Ye ab automatically Streamlit Cloud ki Settings se key uthayega
if "YOUTUBE_API_KEY" in st.secrets:
    API_KEY = st.secrets["YOUTUBE_API_KEY"]
else:
    st.error("API Key missing! Please add YOUTUBE_API_KEY in Streamlit Secrets.")
    st.stop()

# Streamlit App Title
st.title("YouTube Viral Topics Finder 🚀")
st.markdown("Find trending videos on small channels based on specific keywords.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Search Settings")

# 1. Days Input
days = st.sidebar.number_input("Look back (days):", min_value=1, max_value=365, value=7)

# 2. Subscriber Limit
max_subs_limit = st.sidebar.number_input(
    "Max Subscriber Count (Filter):", 
    min_value=0, 
    value=3000, 
    step=500, 
    help="Only show videos from channels with fewer subscribers than this."
)

# 3. Minimum Views
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
    """Parses YouTube duration (PT1M30S) into seconds."""
    if not duration_str: return 0
    match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration_str)
    if not match: return 0
    hours = int(match.group(1)[:-1]) if match.group(1) else 0
    minutes = int(match.group(2)[:-1]) if match.group(2) else 0
    seconds = int(match.group(3)[:-1]) if match.group(3) else 0
    return (hours * 3600) + (minutes * 60) + seconds

def format_seconds_to_time(seconds):
    """Converts seconds to H:MM:SS or MM:SS format"""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}" 
    else:
        return f"{m}:{s:02d}"

def calculate_time_ago(iso_date_str):
    """Calculates relative time."""
    if not iso_date_str: return "Unknown"
    
    published_date = None
    try:
        published_date = datetime.strptime(iso_date_str, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        try:
            published_date = datetime.strptime(iso_date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            return "Unknown"

    now = datetime.utcnow()
    diff = now - published_date
    days = diff.days

    if days >= 365:
        return f"{days // 365} year(s) ago"
    elif days >= 30:
        return f"{days // 30} month(s) ago"
    elif days > 0:
        return f"{days} day(s) ago"
    else:
        hours = diff.seconds // 3600
        return f"{hours} hour(s) ago" if hours > 0 else "Just now"

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
            
            start_date = (datetime.utcnow() - timedelta(days=int(days))).isoformat("T") + "Z"
            
            results_found = False
            total_videos_found = 0

            st.write("---")
            st.info(f"Searching across {len(keywords)} keywords for the last {days} days...")
            progress_bar = st.progress(0)

            for idx, keyword in enumerate(keywords):
                progress_bar.progress((idx + 1) / len(keywords))
                
                # 1. Search
                search_params = {
                    "part": "snippet",
                    "q": keyword,
                    "type": "video",
                    "order": "viewCount",
                    "publishedAfter": start_date,
                    "maxResults": 30, 
                    "key": API_KEY,
                }
                response = requests.get(YOUTUBE_SEARCH_URL, params=search_params)
                data = response.json()

                if "items" not in data or not data["items"]: continue

                videos = data["items"]
                video_ids = [v["id"]["videoId"] for v in videos if "videoId" in v["id"]]
                channel_ids = [v["snippet"]["channelId"] for v in videos if "channelId" in v["snippet"]]

                if not video_ids: continue

                # 2. Video Stats
                stats_params = {"part": "statistics,contentDetails,snippet", "id": ",".join(video_ids), "key": API_KEY}
                stats_response = requests.get(YOUTUBE_VIDEO_URL, params=stats_params)
                stats_data = stats_response.json()
                video_details_map = {item['id']: item for item in stats_data.get('items', [])}

                # 3. Channel Stats
                channel_params = {"part": "statistics,snippet", "id": ",".join(channel_ids), "key": API_KEY}
                channel_response = requests.get(YOUTUBE_CHANNEL_URL, params=channel_params)
                channel_data = channel_response.json()
                channel_map = {item['id']: item for item in channel_data.get('items', [])}

                keyword_results = []
                
                for video in videos:
                    vid_id = video['id']['videoId']
                    ch_id = video['snippet']['channelId']
                    
                    # Video Data
                    vid_details = video_details_map.get(vid_id, {})
                    vid_stats = vid_details.get('statistics', {})
                    vid_content = vid_details.get('contentDetails', {})
                    vid_snippet = vid_details.get('snippet', {}) 
                    
                    views = int(vid_stats.get('viewCount', 0))
                    duration_sec = parse_duration(vid_content.get('duration', "PT0S"))
                    
                    formatted_duration = format_seconds_to_time(duration_sec)
                    video_age = calculate_time_ago(vid_snippet.get('publishedAt'))

                    # Channel Data
                    ch_data = channel_map.get(ch_id, {})
                    subs = int(ch_data.get('statistics', {}).get('subscriberCount', 0))
                    channel_publish_date = ch_data.get('snippet', {}).get('publishedAt')
                    channel_age = calculate_time_ago(channel_publish_date)
                    
                    # Create Channel URL
                    channel_url = f"https://www.youtube.com/channel/{ch_id}"
                    
                    # FILTERS
                    if subs >= max_subs_limit or subs == 0: continue
                    if views < min_views_limit: continue
                    
                    is_short = duration_sec <= shorts_threshold
                    if video_type == "Shorts" and not is_short: continue
                    if video_type == "Long Form" and is_short: continue
                    
                    keyword_results.append({
                        "title": video["snippet"]["title"],
                        "desc": video["snippet"].get("description", "")[:150] + "...",
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                        "thumb": video["snippet"]["thumbnails"]["medium"]["url"],
                        "channel": video["snippet"]["channelTitle"],
                        "channel_url": channel_url,
                        "views": views,
                        "subs": subs,
                        "duration_str": formatted_duration,
                        "video_age": video_age,
                        "channel_age": channel_age
                    })

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
                                
                                # Clickable Channel Name
                                st.markdown(f"📺 **Channel:** [{res['channel']}]({res['channel_url']})") 
                                
                                st.markdown(
                                    f"👁️ **Views:** `{res['views']:,}` | "
                                    f"👥 **Subs:** `{res['subs']:,}` | "
                                    f"⏳ **Duration:** `{res['duration_str']}`"
                                )
                                st.markdown(
                                    f"📅 **Video Age:** {res['video_age']} | "
                                    f"🎂 **Channel Age:** {res['channel_age']}"
                                )
                                st.caption(res['desc'])
                            st.divider()

            if not results_found:
                st.warning("No videos found. Try adjusting filters.")
            else:
                st.success(f"Done! Found {total_videos_found} videos.")

        except Exception as e:
            st.error(f"Error: {e}")
