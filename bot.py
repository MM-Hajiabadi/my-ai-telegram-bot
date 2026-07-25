import os
import sys
import random
import requests
from duckduckgo_search import DDGS

# Retrieving keys from the GitHub Secrets section
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")

# Channel topics for post variety
THEMES = [
    "Artificial Intelligence and Deep Learning breakthroughs",
    "Python programming tips, tricks, and hidden features",
    "MLOps, model deployment, and scaling challenges",
    "Digital electronics, FPGA, and microcontrollers",
    "Linux administration, bash scripting, and networking",
    "Web development, APIs, and automation"
]

def get_llm_response(prompt, system_prompt="You are a helpful AI assistant."):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/MM-Hajiabadi/my-ai-telegram-bot",
    }
    data = {
        "model": "google/gemini-2.5-flash:free", # choose a free model
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error querying OpenRouter: {e}")
        return None

def search_web(query):
    try:
        print(f"Searching DuckDuckGo for: '{query}'")
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=4))
            summary_text = ""
            for i, r in enumerate(results, 1):
                summary_text += f"{i}. Title: {r.get('title')}\nSnippet: {r.get('body')}\nLink: {r.get('href')}\n\n"
            return summary_text
    except Exception as e:
        print(f"DuckDuckGo search failed: {e}")
        return None

def get_pexels_image(query):
    if not PEXELS_API_KEY:
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
    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    if image_url and len(text) <= 1000:
        url = f"{base_url}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": image_url,
            "caption": text,
            "parse_mode": "HTML"
        }
    else:
        if image_url:
            try:
                requests.post(f"{base_url}/sendPhoto", json={"chat_id": TELEGRAM_CHAT_ID, "photo": image_url}, timeout=15)
            except Exception:
                pass
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
        print("Post sent successfully!")
        return True
    except Exception as e:
        print(f"Error sending to Telegram: {e}")
        return False

def main():
    if not OPENROUTER_API_KEY or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Critical environment variables missing!")
        sys.exit(1)
        
    theme = random.choice(THEMES)
    prompt_q = f"Generate one interesting, practical, and real-world question or technical challenge related to '{theme}'. Return ONLY the English search query or keywords that we should search on Google to find the best, most up-to-date solution for this problem. No introduction, no markdown, just the raw search query."
    search_query = get_llm_response(prompt_q, "You are a specialized technical assistant. You only output precise search keywords.")
    
    if not search_query:
        search_query = f"latest trends in {theme}"
    
    search_results = search_web(search_query)
    
    if search_results:
        prompt_post = f"""
Based on the following search results about "{search_query}":
---
{search_results}
---
Write a highly engaging, informative, and professional Telegram post in English).
Requirements:
1. Explain the problem/concept clearly.
2. Provide a practical solution, code snippet, or key takeaway.
3. Use a friendly, technical, and premium tone.
4. Use appropriate emojis.
5. Format in HTML for Telegram (use <b>bold</b>, <i>italic</i>, and <code>code</code> tags. No markdown like ** or `).
6. Under 900 characters.
7. End with an engaging question.
8. Use relevant hashtags. A maximum of three.
"""
    else:
        prompt_post = f"Write an engaging English tech post about '{search_query}'. Under 900 chars, HTML format, with code snippet."

    post_content = get_llm_response(prompt_post, "You write beautiful, formatted English posts for a premium Telegram channel about AI and technology. Always use HTML tags.")
    if not post_content:
        sys.exit(1)
        
    img_prompt = f"Extract 1 or 2 simple English words representing: '{search_query}'. Example: 'coding' or 'database'. Return ONLY the keywords, no other text."
    img_keywords = get_llm_response(img_prompt, "You output only 1-2 keywords.")
    image_url = get_pexels_image(img_keywords or "technology")
    
    if not image_url:
        fallback_images = [
            "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800",
            "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800",
            "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800"
        ]
        image_url = random.choice(fallback_images)
        
    send_telegram_post(post_content, image_url)

if __name__ == "__main__":
    main()
