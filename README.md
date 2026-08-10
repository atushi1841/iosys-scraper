# IOSYS Scraper (中古スマホ・タブレット)

Scrapes product listings from [iosys.co.jp](https://www.iosys.co.jp), a leading Japanese second-hand smartphone/tablet retailer. Collects price, rank, stock, release date, and specifications for used phones, tablets, and mobile routers.

## Output Sample

```json
{
  "productId": "336691",
  "title": "Rakuten WiFi Pocket Platinum T99W541 ホワイト【楽天版 SIMフリー】",
  "brand": "楽天",
  "price": 6980,
  "rank": "未使用品",
  "stock": 641,
  "release": "2024/07",
  "condition": "未使用品",
  "spec": "対応サービス:LTE(1/3/7/18/19/26/28A/38/41) 形状:モバイルルーター Wi-Fi:b/g/n 最大速度:150Mbps(下り)/50Mbps(上り) 最大同時接続数:16台(Wi-Fi)/1台(USB) サイズ:約65(H)x96.5(W)x15.3(D)mm 重量:約103g バッテリー:2440mAh SIMサイズ:nanoSIM 発売日:2024/7 接続端子:Type-C",
  "imageUrl": "https://d27ea4kkb8flj9.cloudfront.net/336691_1_S.jpg",
  "productUrl": "https://www.iosys.co.jp/items/mobile-router/rakuten/rakuten_wifi_pockett99w541/336691",
  "scrapedAt": "2026-08-10T10:03:54Z"
}
```

## Input

| Field | Type | Default | Description |
|---|---|---|---|
| `searchKeyword` | string | `iPhone` | Search keyword |
| `maxItems` | integer | 100 | Max items to collect |
| `maxPages` | integer | 2 | Max pages to scrape |

## Use Cases

- **Used phone price monitoring** — track iPhone/Android resale values
- **Stock tracking** — monitor inventory across IOSYS stores
- **Reseller arbitrage** — find underpriced devices

## Integrations

Works with Apify [Connectors](https://apify.com/integrations) — push results to Slack, Google Sheets, Notion, or Supabase with one click. Trigger on a [Schedule](https://apify.com/docs/schedules) for daily price tracking.

## Pricing

Pay per event — $0.00005/run + $0.002/item.
