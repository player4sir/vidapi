import os
import asyncio
from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel
from bs4 import BeautifulSoup
import httpx
import re
from urllib.parse import urljoin
from typing import List, Optional

app = FastAPI()

BASE_URL = os.getenv('BASE_URL', 'https://www.hsck.la')

async def fetch_with_retry(url: str, max_retries: int = 3) -> str:
    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as e:
                if attempt == max_retries - 1:
                    raise HTTPException(status_code=500, detail=f"Error fetching {url}: {str(e)}")
                await asyncio.sleep(1)

class VideoItem(BaseModel):
    vid: str
    title: str
    image: str
    quality: str
    full_title: str
    play_count: str
    date: str
    m3u8_link: Optional[str] = None

def extract_item_data(item: BeautifulSoup) -> Optional[VideoItem]:
    thumb = item.select_one('a.stui-vodlist__thumb')
    detail = item.select_one('div.stui-vodlist__detail')

    if not thumb or not detail:
        return None

    href = thumb.get('href', '')
    vid_match = re.search(r'/id/(\d+)/', href)
    vid = vid_match.group(1) if vid_match else ''

    return VideoItem(
        vid=vid,
        title=thumb.get('title', ''),
        image=thumb.get('data-original', ''),
        quality=thumb.select_one('span.pic-text').text if thumb.select_one('span.pic-text') else '',
        full_title=detail.select_one('h4.title a').text if detail.select_one('h4.title a') else '',
        play_count=detail.select_one('p.sub span.pull-right').text if detail.select_one('p.sub span.pull-right') else '',
        date=detail.select_one('p.sub').contents[-1].strip() if detail.select_one('p.sub') else ''
    )

def extract_m3u8_link(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, 'html.parser')
    script = soup.find('script', string=lambda t: t and 'player_aaaa' in t)
    if script:
        match = re.search(r'"url":"(.*?)"', script.string)
        if match:
            return match.group(1).replace('\\', '')
    return None

async def fetch_item_details(item: VideoItem) -> VideoItem:
    detail_url = urljoin(BASE_URL, f'/index.php/vod/play/id/{item.vid}/sid/1/nid/1.html')
    detail_html = await fetch_with_retry(detail_url)
    item.m3u8_link = extract_m3u8_link(detail_html)
    return item

class VideoQuery(BaseModel):
    category: int
    page: int = Query(1, ge=1)
    per_page: int = Query(20, ge=1, le=100)

class VideoResponse(BaseModel):
    category: int
    page: int
    per_page: int
    total_items: int
    has_next: bool
    items: List[VideoItem]

@app.get("/api/videos", response_model=VideoResponse)
async def get_videos(query: VideoQuery = Depends()) -> VideoResponse:
    try:
        url = urljoin(BASE_URL, f'/index.php/vod/type/id/{query.category}/page/{query.page}.html')
        
        html = await fetch_with_retry(url)
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select('li .stui-vodlist__box')
        
        extracted_items = [extract_item_data(item) for item in items[:query.per_page] if extract_item_data(item)]
        
        tasks = [fetch_item_details(item) for item in extracted_items]
        detailed_items = await asyncio.gather(*tasks)

        return VideoResponse(
            category=query.category,
            page=query.page,
            per_page=query.per_page,
            total_items=len(items),
            has_next=len(items) > query.per_page,
            items=detailed_items
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
