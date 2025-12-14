import streamlit as st
import requests
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Viral Topic Finder", layout="wide")

# !!! API KEY HARDCODED HERE !!!
API_KEY = "AIzaSyDjTun06qZ6n4Ud84zZes71IgoJWYlD19o"

# Streamlit App Title
st.title("YouTube Viral Topics Finder 🚀")
st.markdown("Specific keywords par aisi videos dhoondien jo chote channels par viral ho rahi hain.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Search Settings")

# 1. Days Input (Duration)
days = st.sidebar.number_input("Search videos from last (days):", min_value=1, max_value=365, value=7)

# 2. Subscriber Limit Input
max_subs_limit = st.sidebar.number_input(
    "Max Subscriber Count (Filter):", 
    min_value=0, 
    value=3000, 
    step=500, 
    help="Sirf un channels ki videos dikhayega jinke subscribers is number se kam honge."
)

# 3. Keywords Input
st.subheader("Enter Keywords")
st.markdown("Apne topics neeche likhein. Comma (`,`) ya New Line se alag karein.")
keyword_input = st.text_area(
    "Keywords:", 
    height=150,
    placeholder="Example:\nDigital Marketing,\nAffiliate Marketing,\nEarn Money Online"
)

# --- LOGIC TO PROCESS INPUT ---
def get_keywords_list(raw_input):
    if not raw_input:
        return []
    # Replace newlines with commas, then split by comma
    items = raw_input.replace("\n", ",").split(",")
    # Strip whitespace and remove empty strings
    return [item.strip() for item in items if item.strip()]

keywords = get_keywords_list(keyword_input)

# --- FETCH DATA BUTTON ---
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
                    "maxResults": 15, # Fetch extra to account for filtering
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

                # Fetch video statistics (for views)
                stats_params = {"part": "statistics", "id": ",".join(video_ids), "key": API_KEY}
                stats_response = requests.get(YOUTUBE_VIDEO_URL, params=stats_params)
                stats_data = stats_response.json()

                # Fetch channel statistics (for subscriber count)
                channel_params = {"part": "statistics", "id": ",".join(channel_ids), "key": API_KEY}
                channel_response = requests.get(YOUTUBE_CHANNEL_URL, params=channel_params)
                channel_data = channel_response.json()

                # Map data for easy access
                video_stats_map = {item['id']: item['statistics'] for item in stats_data.get('items', [])}
                channel_stats_map = {item['id']: item['statistics'] for item in channel_data.get('items', [])}

                # Process and Filter
                keyword_results = []
                
                for video in videos:
                    vid_id = video['id']['videoId']
                    ch_id = video['snippet']['channelId']
                    
                    # Get stats safely
                    views = int(video_stats_map.get(vid_id, {}).get('viewCount', 0))
                    subs_raw = channel_stats_map.get(ch_id, {}).get('subscriberCount', 0)
                    
                    # Hidden subscribers handling (treat as 0 or ignore based on preference, here we treat as 0)
                    subs = int(subs_raw) if subs_raw else 0 
                    
                    # MAIN FILTER: Check user defined subscriber limit
                    # subs > 0 check ensures we don't pick up hidden subscriber channels if you don't want them
                    if subs < max_subs_limit and subs > 0: 
                        keyword_results.append({
                            "title": video["snippet"]["title"],
                            "desc": video["snippet"].get("description", "")[:150] + "...",
                            "url": f"https://www.youtube.com/watch?v={vid_id}",
                            "views": views,
                            "subs": subs,
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
                                st.markdown(f"👁️ **Views:** `{res['views']:,}` | 👥 **Subs:** `{res['subs']:,}`")
                                st.caption(res['desc'])
                            st.divider()

            if not results_found:
                st.warning("No videos found matching your criteria (Low Subscribers + High Views). Try increasing days or subscriber limit.")
            else:
                st.success(f"Search Complete! Total videos found: {total_videos_found}")

        except Exception as e:
            st.error(f"An error occurred: {e}")
