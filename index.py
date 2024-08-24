from fastapi import FastAPI, Query
import httpx
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import random
from mangum import Mangum

app = FastAPI()

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36'
]

async def fetch(url, retries=5):
    async with httpx.AsyncClient() as client:
        for attempt in range(retries):
            try:
                headers = {'User-Agent': random.choice(user_agents)}
                response = await client.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as e:
                print(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt == retries - 1:
                    print(f"Error fetching {url}: {str(e)}")
                    return None
                await asyncio.sleep(2 ** attempt)

def extract_item_data(item):
    thumb = item.select_one('a.stui-vodlist__thumb')
    detail = item.select_one('div.stui-vodlist__detail')

    if not thumb or not detail:
        return None

    href = thumb.get('href', '')
    vid_match = re.search(r'/id/(\d+)/', href)
    vid = vid_match.group(1) if vid_match else ''

    return {
        "vid": vid,
        "title": thumb.get('title', ''),
        "image": thumb.get('data-original', ''),
        "quality": thumb.select_one('span.pic-text').text if thumb.select_one('span.pic-text') else '',
        "full_title": detail.select_one('h4.title a').text if detail.select_one('h4.title a') else '',
        "play_count": detail.select_one('p.sub span.pull-right').text if detail.select_one('p.sub span.pull-right') else '',
        "date": detail.select_one('p.sub').contents[-1].strip() if detail.select_one('p.sub') else ''
    }

def extract_m3u8_link(html):
    soup = BeautifulSoup(html, 'html.parser')
    script = soup.find('script', string=lambda t: t and 'player_aaaa' in t)
    if script:
        match = re.search(r'"url":"(.*?)"', script.string)
        if match:
            return match.group(1).replace('\\', '')
    return None

async def process_page(url):
    html = await fetch(url)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    items = soup.select('li .stui-vodlist__box')

    return [item_data for item in items if (item_data := extract_item_data(item))]

async def process_detail_pages(base_url, items):
    async def fetch_m3u8(item):
        detail_url = urljoin(base_url, f'/index.php/vod/play/id/{item["vid"]}/sid/1/nid/1.html')
        html = await fetch(detail_url)
        if html:
            item['m3u8_link'] = extract_m3u8_link(html)
        return item

    return await asyncio.gather(*[fetch_m3u8(item) for item in items])

@app.get("/api/videos")
async def get_videos(
    base_url: str = Query(..., description="Base URL of the website"),
    category: int = Query(..., description="Category ID"),
    page: int = Query(1, description="Page number", ge=1),
    per_page: int = Query(20, description="Items per page", ge=1, le=100)
):
    try:
        url = urljoin(base_url, f'/index.php/vod/type/id/{category}/page/{page}.html')
        items = await process_page(url)

        # Process only the number of items specified by per_page
        items = items[:per_page]

        # Fetch m3u8 links for the items
        items_with_m3u8 = await process_detail_pages(base_url, items)

        return {
            "category": category,
            "page": page,
            "per_page": per_page,
            "items": items_with_m3u8
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/test")
async def test():
    return {"message": "API is working!"}

# 使用 Mangum 处理器
handler = Mangum(app)
