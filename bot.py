import os
import sys
import random
import requests
from duckduckgo_search import DDGS

# Get secrets from GitHub Environment Variables
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

# Channel themes
THEMES = [
    "Artificial Intelligence and Deep Learning breakthroughs",
    "Python programming tips, tricks, and hidden features",
    "MLOps, model deployment, and scaling challenges",
    "Digital electronics, FPGA, and microcontrollers",
    "Linux administration, bash scripting, and networking",
    "Web development, APIs, and automation"
]

def get_llm_response(prompt, system_prompt="You are a helpful AI assistant."):
    """Helper to query OpenRouter using a free model."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # Using gemini-2.5-flash which is extremely fast, free, and robust
    data = {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
        
        # Check if HTTP request failed (like 401, 404, 500)
        if response.status_code != 200:
            print(f"OpenRouter API returned error code {response.status_code}: {response.text}")
            return None
            
        res_json = response.json()
        if 'choices' in res_json and len(res_json['choices']) > 0:
            return res_json['choices'][0]['message']['content'].strip()
        else:
            print(f"Unexpected response format from OpenRouter: {res_json}")
            return None
    except Exception as e:
        print(f"Error querying OpenRouter: {e}")
        return None

def search_web(query):
    """Search the web using DuckDuckGo (Free, no API key needed)."""
    try:
        print(f"Searching DuckDuckGo for: '{query}'")
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=4))
        summary_text = ""
        for i, r in enumerate(results, 1):
            summary_text += f"{i}. Title: {r.get('title')}\nSnippet: {r.get('body')}\nLink: {r.get('href')}\n\n"
        return summary_text
    except Exception as e:
        print(f"DuckDuckGo search failed (using fallback): {e}")
        return None

def get_pexels_image(query):
    """Fetch a high-quality relevant image from Pexels."""
    if not PEXELS_API_KEY:
        print("Pexels API Key not provided. Skipping image search.")
        return None
    
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("photos"):
            return data["photos"][0]["src"]["large"]
    except Exception as e:
        print(f"Error fetching from Pexels: {e}")
    return None

def send_telegram_post(text, image_url=None):
    """Send the final post to Telegram as a single unified message (photo with caption)."""
    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    
    # Ensure text is not exceeding Telegram's 1024-character caption limit.
    # If it is slightly over, we truncate to 1020 chars and add "..." to guarantee they are posted together.
    if len(text) > 1024:
        print(f"Warning: Post length ({len(text)}) exceeds Telegram's caption limit of 1024. Truncating...")
        text = text[:1020] + "..."
        
    if image_url:
        print("Sending photo with unified caption...")
        url = f"{base_url}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": image_url,
            "caption": text,
            "parse_mode": "HTML"
        }
    else:
        print("No image URL provided. Sending text-only message...")
        url = f"{base_url}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        
    try:
        response = requests.post(url, json=payload, timeout=20)
        response.raise_for_status()
        print("Telegram post sent successfully!")
        return True
    except Exception as e:
        print(f"Error sending to Telegram: {e}")
        if response is not None:
            print(f"Response details: {response.text}")
        return False

def main():
    # Verify environment variables
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY is not set or empty in GitHub Secrets!")
        sys.exit(1)
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set or empty in GitHub Secrets!")
        sys.exit(1)
    if not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_CHAT_ID is not set or empty in GitHub Secrets!")
        sys.exit(1)
        
    theme = random.choice(THEMES)
    print(f"Selected Theme: {theme}")
    
    # Step 1: Generate search query using OpenRouter
    prompt_q = f"Generate one interesting, practical, and real-world question or technical challenge related to '{theme}'. Return ONLY the English search query or keywords that we should search on Google to find the best, most up-to-date solution for this problem. No introduction, no markdown, just the raw search query."
    search_query = get_llm_response(prompt_q, "You are a specialized technical assistant. You only output precise search keywords.")
    
    if not search_query:
        print("Could not generate search query using OpenRouter. Using default query.")
        search_query = f"latest trends in {theme}"
    
    print(f"Generated search query: '{search_query}'")
    
    # Step 2: Search the web
    search_results = search_web(search_query)
    
    # Step 3: Write the post
    # We strictly enforce length limit (max 750 characters) in the prompt to leave room for HTML tags.
    if search_results:
        prompt_post = f"""
Based on the following search results about "{search_query}":
---
{search_results}
---

Write an exceptionally engaging, informative, and professional Telegram post in English.
Requirements:
1. Explain the problem/concept clearly.
2. Provide a practical solution, code snippet, or key takeaway.
3. Use a friendly, technical, and premium tone with appropriate emojis.
4. Format in clean HTML for Telegram (use only <b>bold</b>, <i>italic</i>, and <code>code</code> tags. NO markdown).
5. CRITICAL: The entire post including HTML tags MUST be under 750 characters. Keep it concise, high-density, and impactful.
6. End with an engaging question.
"""
    else:
        prompt_post = f"""
Write an engaging English tech post about "{search_query}".
Requirements:
1. Explain the technical concept clearly.
2. Provide a practical solution or code snippet.
3. Use a friendly, technical, and premium tone with appropriate emojis.
4. Format in clean HTML (use only <b>, <i>, and <code>. NO markdown).
5. CRITICAL: The entire post including HTML tags MUST be under 750 characters.
6. End with an engaging question.
"""

    post_content = get_llm_response(prompt_post, "You are a master technical content writer. You write beautiful, high-density, formatted English posts for a Telegram channel. You are extremely strict about keeping the text brief (under 750 characters) so it fits as an image caption.")
    if not post_content:
        print("ERROR: Failed to generate post content.")
        sys.exit(1)
        
    print("Generated Post Content:")
    print(post_content)
    
    # Step 4: Get image
    img_prompt = f"Extract 1 or 2 simple English words suitable for finding a high-quality abstract tech photo on Pexels representing: '{search_query}'. Example: 'artificial intelligence' or 'coding' or 'server'. Return ONLY the keywords, no other text."
    img_keywords = get_llm_response(img_prompt, "You output only 1-2 keywords.")
    if not img_keywords:
        img_keywords = "technology"
    
    print(f"Image search keywords: '{img_keywords}'")
    image_url = get_pexels_image(img_keywords)
    
    if not image_url:
        fallback_images = [
            "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800",
            "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800",
            "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800",
            "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=800"
        ]
        image_url = random.choice(fallback_images)
        print(f"Using fallback image: {image_url}")
        
    # Step 5: Send to Telegram
    send_telegram_post(post_content, image_url)

if __name__ == "__main__":
    main()
