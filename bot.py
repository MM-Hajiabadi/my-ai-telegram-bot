import os
import sys
import random
import re
import requests
from ddgs import DDGS

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

# ==============================================================
# HTML SAFETY FUNCTIONS for Telegram
# ==============================================================

ALLOWED_TAGS = {"b", "i", "code", "pre", "a", "strong", "em", "s", "u"}

def fix_html_tags(text):
    """
    Fix common Telegram HTML issues:
    1. Remove unknown/disallowed tags entirely.
    2. Auto-close unclosed allowed tags.
    3. Replace mismatched closing tags.
    """
    # Step 1: Remove all tags that are NOT in ALLOWED_TAGS
    def strip_disallowed(match):
        full = match.group(0)
        if full.startswith('</'):
            tag_name = full[2:-1].split()[0].rstrip('>')
        else:
            tag_name = full[1:].split()[0].rstrip('>').split('<')[0]
        if tag_name.lower() not in ALLOWED_TAGS:
            return ''
        return full

    text = re.sub(r'</?[\w\-]+(?:\s[^>]*)?>', strip_disallowed, text)

    # Step 2: Build a stack of opening tags; auto-close unclosed ones
    stack = []
    i = 0
    result_chars = []
    
    while i < len(text):
        close_match = re.match(r'</(\w+)>', text[i:])
        if close_match:
            tag = close_match.group(1).lower()
            if tag in ALLOWED_TAGS:
                if stack and stack[-1] == tag:
                    stack.pop()
                    result_chars.append(f'</{tag}>')
                elif tag in stack:
                    while stack and stack[-1] != tag:
                        stack.pop()
                    if stack and stack[-1] == tag:
                        stack.pop()
                    result_chars.append(f'</{tag}>')
                else:
                    pass  # ignore orphan closing tag
            i += len(close_match.group(0))
            continue
        
        open_match = re.match(r'<(\w+)(\s[^>]*)?>', text[i:])
        if open_match:
            tag = open_match.group(1).lower()
            if tag in ALLOWED_TAGS and tag not in ('br', 'hr', 'img', 'input', 'meta', 'link'):
                stack.append(tag)
                result_chars.append(open_match.group(0))
            i += len(open_match.group(0))
            continue
        
        sc_match = re.match(r'<(\w+)\s*/?>', text[i:])
        if sc_match and sc_match.group(1).lower() in ALLOWED_TAGS:
            result_chars.append(sc_match.group(0))
            i += len(sc_match.group(0))
            continue
        
        result_chars.append(text[i])
        i += 1
    
    for tag in reversed(stack):
        result_chars.append(f'</{tag}>')
    
    return ''.join(result_chars)


def safe_truncate_html(html_text, max_length=1000):
    """Truncate HTML without breaking tags."""
    if len(html_text) <= max_length:
        return html_text
    
    truncated = html_text[:max_length]
    truncated = re.sub(r'<[^>]*$', '', truncated)
    
    stack = []
    i = 0
    result_chars = []
    
    while i < len(truncated):
        close_match = re.match(r'</(\w+)>', truncated[i:])
        if close_match:
            tag = close_match.group(1).lower()
            if tag in ALLOWED_TAGS:
                if stack and stack[-1] == tag:
                    stack.pop()
                elif tag in stack:
                    while stack and stack[-1] != tag:
                        stack.pop()
                    if stack and stack[-1] == tag:
                        stack.pop()
            i += len(close_match.group(0))
            result_chars.append(close_match.group(0))
            continue
        
        open_match = re.match(r'<(\w+)(\s[^>]*)?>', truncated[i:])
        if open_match:
            tag = open_match.group(1).lower()
            if tag in ALLOWED_TAGS and tag not in ('br', 'hr', 'img', 'input', 'meta', 'link'):
                stack.append(tag)
            result_chars.append(open_match.group(0))
            i += len(open_match.group(0))
            continue
        
        result_chars.append(truncated[i])
        i += 1
    
    for tag in reversed(stack):
        result_chars.append(f'</{tag}>')
    
    return ''.join(result_chars) + '...'


def make_telegram_safe(text, max_length=1000):
    """Full pipeline: fix HTML tags, then safely truncate."""
    text = fix_html_tags(text)
    text = safe_truncate_html(text, max_length)
    return text


# ==============================================================
# CORE FUNCTIONS
# ==============================================================

def get_llm_response(prompt, system_prompt="You are a helpful AI assistant."):
    """Helper to query OpenRouter using a free model."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
        
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
    """Send post to Telegram with multiple fallback layers."""
    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    
    text = make_telegram_safe(text, max_length=1000)
    
    # Attempt 1: Photo + HTML caption
    if image_url:
        print(f"Sending photo with HTML caption... Image URL: {image_url}")
        try:
            response = requests.post(f"{base_url}/sendPhoto", json={
                "chat_id": TELEGRAM_CHAT_ID,
                "photo": image_url,
                "caption": text,
                "parse_mode": "HTML"
            }, timeout=20)
            if response.status_code == 200:
                print("Post sent successfully (Photo+HTML)!")
                return True
            print(f"Photo+HTML failed ({response.status_code}): {response.text}")
        except Exception as e:
            print(f"Photo+HTML exception: {e}")
    
    # Attempt 2: Photo + Plain text caption
    if image_url:
        plain = re.sub(r'<[^>]+>', '', text)
        if len(plain) > 1024:
            plain = plain[:1021] + '...'
        print("Attempt 2: Photo + plain caption...")
        try:
            response = requests.post(f"{base_url}/sendPhoto", json={
                "chat_id": TELEGRAM_CHAT_ID,
                "photo": image_url,
                "caption": plain
            }, timeout=20)
            if response.status_code == 200:
                print("Post sent successfully (Photo+Plain)!")
                return True
        except Exception as e:
            print(f"Attempt 2 failed: {e}")
    
    # Attempt 3: Text-only with HTML
    print("Attempt 3: Text-only with HTML...")
    try:
        response = requests.post(f"{base_url}/sendMessage", json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=20)
        if response.status_code == 200:
            print("Post sent successfully (Text+HTML)!")
            return True
        print(f"Attempt 3 failed ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"Attempt 3 exception: {e}")
    
    # Attempt 4: Plain text only
    plain = re.sub(r'<[^>]+>', '', text)
    print("Attempt 4: Plain text only...")
    try:
        response = requests.post(f"{base_url}/sendMessage", json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": plain
        }, timeout=20)
        if response.status_code == 200:
            print("Post sent successfully (Plain)!")
            return True
        print(f"Attempt 4 failed: {response.text}")
    except Exception as e:
        print(f"Attempt 4 exception: {e}")
    
    raise Exception("All 4 send attempts failed.")

def main():
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY is not set!")
        sys.exit(1)
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set!")
        sys.exit(1)
    if not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_CHAT_ID is not set!")
        sys.exit(1)
        
    theme = random.choice(THEMES)
    print(f"Selected Theme: {theme}")
    
    prompt_q = f"Generate one interesting, practical, and real-world question or technical challenge related to '{theme}'. Return ONLY the English search query or keywords that we should search on Google to find the best solution. No introduction, no markdown, just the raw search query."
    search_query = get_llm_response(prompt_q, "You only output precise search keywords.")
    
    if not search_query:
        search_query = f"latest trends in {theme}"
    
    print(f"Query: '{search_query}'")
    search_results = search_web(search_query)
    
    if search_results:
        prompt_post = f"""
Based on the following search results about "{search_query}":
---
{search_results}
---

Write an engaging Telegram post in English.
Requirements:
1. Explain the problem/concept clearly.
2. Provide a solution or key takeaway.
3. Use emojis, friendly technical tone.
4. HTML format (only <b>, <i>, <code>. NO markdown).
5. MUST be under 750 characters total.
6. End with a question.
7. Add up to 3 hashtags.
"""
    else:
        prompt_post = f"""
Write an engaging English tech post about "{search_query}".
Requirements:
1. Explain the concept clearly.
2. Provide a solution or code snippet.
3. Use emojis, friendly tone.
4. HTML format (only <b>, <i>, <code>. NO markdown).
5. MUST be under 750 characters.
6. End with a question.
7. Add up to 3 hashtags.
"""

    post_content = get_llm_response(prompt_post, "You write concise HTML-formatted posts for Telegram. Strictly under 750 characters.")

    if not post_content:
        print("ERROR: Failed to generate post content.")
        sys.exit(1)
    
    print(f"Post ({len(post_content)} chars):")
    print(post_content)
    
    img_prompt = f"Extract 1-2 English keywords for a Pexels photo representing: '{search_query}'. Example: 'artificial intelligence'. Return ONLY keywords."
    img_keywords = get_llm_response(img_prompt, "Output only 1-2 keywords.")
    if not img_keywords:
        img_keywords = "technology"
    
    print(f"Image keywords: '{img_keywords}'")
    image_url = get_pexels_image(img_keywords)
    
    if not image_url:
        fallback_images = [
            "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800",
            "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800",
            "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800",
            "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=800"
        ]
        image_url = random.choice(fallback_images)
        print(f"Fallback image: {image_url}")
    
    send_telegram_post(post_content, image_url)

if __name__ == "__main__":
    main()
