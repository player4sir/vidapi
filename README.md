# 视频信息 API 使用说明

这个 API 允许用户获取特定类别的视频信息，包括标题、图片、播放次数和 m3u8 链接等。

## API 端点

GET `/api/videos`

## 请求参数

- `category` (必需): 整数，表示视频类别的 ID。
- `page` (可选): 整数，默认值为 1，表示要获取的页码。
- `per_page` (可选): 整数，默认值为 20，范围 1-100，表示每页返回的项目数。

## 示例请求

```
GET /api/videos?category=1&page=1&per_page=20
```

## 返回数据

API 返回一个 JSON 对象，包含以下字段：

- `category`: 请求的类别 ID
- `page`: 当前页码
- `per_page`: 每页项目数
- `total_items`: 当前页面上的总项目数
- `has_next`: 布尔值，表示是否有下一页
- `items`: 包含视频信息的数组，每个项目包含以下字段：
  - `vid`: 视频 ID
  - `title`: 视频标题
  - `image`: 视频封面图片 URL
  - `quality`: 视频质量
  - `full_title`: 完整标题
  - `play_count`: 播放次数
  - `date`: 发布日期
  - `m3u8_link`: m3u8 播放链接

## 示例响应

```json
{
  "category": 1,
  "page": 1,
  "per_page": 20,
  "total_items": 25,
  "has_next": true,
  "items": [
    {
      "vid": "12345",
      "title": "示例视频",
      "image": "https://example.com/image.jpg",
      "quality": "HD",
      "full_title": "示例视频 - 完整标题",
      "play_count": "1000次播放",
      "date": "2023-08-24",
      "m3u8_link": "https://example.com/video.m3u8"
    },
    // ... 更多项目
  ]
}
```

## 错误处理

如果发生错误，API 将返回一个包含错误详情的 JSON 对象，HTTP 状态码将反映错误类型。

## 注意事项

- 请合理使用 API，避免过于频繁的请求。
- API 的基础 URL 可能会根据部署环境而变化，请向 API 提供者确认正确的基础 URL。
