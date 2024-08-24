from mangum import Mangum
from fastapi import FastAPI, Query, HTTPException
import httpx
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import asyncio

app = FastAPI()

async def fetch(url: str, client: httpx.AsyncClient):
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Error fetching {url}: {str(e)}")

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

async def process_page(url: str, client: httpx.AsyncClient):
    html = await fetch(url, client)
    soup = BeautifulSoup(html, 'html.parser')
    items = soup.select('li .stui-vodlist__box')
    return [item_data for item in items if (item_data := extract_item_data(item))]

async def process_detail_pages(base_url: str, items: list, client: httpx.AsyncClient):
    async def fetch_m3u8(item):
        detail_url = urljoin(base_url, f'/index.php/vod/play/id/{item["vid"]}/sid/1/nid/1.html')
        html = await fetch(detail_url, client)
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
    url = urljoin(base_url, f'/index.php/vod/type/id/{category}/page/{page}.html')
    
    async with httpx.AsyncClient() as client:
        items = await process_page(url, client)
        items = items[:per_page]
        items_with_m3u8 = await process_detail_pages(base_url, items, client)

    return {
        "category": category,
        "page": page,
        "per_page": per_page,
        "items": items_with_m3u8
    }

handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
