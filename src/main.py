import asyncio
import json
import random
import re
import sys
from datetime import datetime, timezone
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup

try:
    from apify import Actor
except ImportError:
    Actor = None

BASE_URL = "https://www.iosys.co.jp"


def parse_item(li):
    # Hidden fields – the most reliable source for gn/name/rank/spec
    hidden = {}
    for inp in li.find_all("input", type="hidden"):
        name = inp.get("name")
        value = inp.get("value", "").strip()
        if name in ("gn", "name", "rank", "spec"):
            hidden[name] = value

    product_id = hidden.get("gn", "")

    # Title from hidden input, fallback to p.name, then anchor text
    title = hidden.get("name", "")
    if not title:
        p_name = li.select_one("p.name")
        if p_name:
            title = p_name.get_text(" ", strip=True)
    if not title:
        a = li.select_one("a[href]")
        if a:
            title = a.get_text(" ", strip=True)

    # Brand from "メーカー：SAMSUNG"
    brand = ""
    maker_el = li.select_one("p.maker")
    if maker_el:
        maker_text = maker_el.get_text(" ", strip=True)
        m = re.search(r"[：:]\s*(.+)", maker_text)
        brand = m.group(1).strip() if m else maker_text.replace("メーカー", "").strip(" ：:")

    # Price from "124,800円"
    price = 0
    price_el = li.select_one("div.price p")
    if price_el:
        price_text = price_el.get_text(" ", strip=True)
        price_match = re.search(r"([\d,]+)\s*円", price_text)
        if price_match:
            price = int(price_match.group(1).replace(",", ""))

    # Stock from "在庫数：4"
    stock = 0
    stock_el = li.select_one("p.stock")
    if stock_el:
        stock_text = stock_el.get_text(" ", strip=True)
        stock_match = re.search(r"(\d+)", stock_text)
        if stock_match:
            stock = int(stock_match.group(1))

    # Release from "発売日： 2026/03"
    release = ""
    release_el = li.select_one("p.release")
    if release_el:
        release_text = release_el.get_text(" ", strip=True)
        release_match = re.search(r"(\d{4}/\d{1,2})", release_text)
        release = release_match.group(1) if release_match else release_text

    # Condition from div.rank p.condition
    condition = ""
    cond_el = li.select_one("div.rank p.condition")
    if cond_el:
        condition = cond_el.get_text(" ", strip=True)
    if not condition:
        condition = hidden.get("rank", "")

    rank = hidden.get("rank", "") or condition
    spec = hidden.get("spec", "")

    # Product URL and image URL
    product_url = ""
    image_url = ""
    a_el = li.select_one("a[href]")
    if a_el:
        href = a_el.get("href")
        if href:
            product_url = urljoin(BASE_URL, href)

    img_el = li.select_one("img")
    if img_el:
        # lozad遅延ロード: data-srcに実URL(dummy.gifはプレースホルダ)
        src = (
            img_el.get("data-src")
            or img_el.get("data-original")
            or img_el.get("src")
        )
        if src and "dummy.gif" not in src:
            image_url = urljoin(BASE_URL, src)

    return {
        "productId": product_id,
        "title": title,
        "brand": brand,
        "price": price,
        "rank": rank,
        "stock": stock,
        "release": release,
        "condition": condition,
        "spec": spec,
        "imageUrl": image_url,
        "productUrl": product_url,
        "scrapedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


async def fetch_page(client, url):
    for attempt in range(3):
        try:
            resp = await client.get(url)
            print(f"[DEBUG] GET {url} -> {resp.status_code} size={len(resp.text)}", flush=True)
            if resp.status_code == 200:
                resp.encoding = "utf-8"
                return resp.text
            if resp.status_code in (429, 500, 502, 503, 504):
                raise httpx.HTTPStatusError(
                    f"HTTP {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            # Any other non-200 status: treat as no data
            return None
        except Exception as exc:
            print(f"[DEBUG] attempt={attempt} error={type(exc).__name__}: {str(exc)[:150]}", flush=True)
            if attempt == 2:
                raise
            wait = 2 ** attempt
            await asyncio.sleep(wait + random.uniform(0.5, 1.5))
    return None


async def main():
    if Actor is not None:
        await Actor.init()
    print("[DEBUG] main started", flush=True)

    try:
        actor_input = await Actor.get_input() if Actor is not None else None
        print(f"[DEBUG] actor_input: {actor_input}", flush=True)
        if not actor_input:
            raw_input = sys.stdin.read()
            actor_input = json.loads(raw_input) if raw_input.strip() else {}
        keyword = actor_input.get("keyword", "iPhone")
        max_items = int(actor_input.get("maxItems", 100))
        if max_items <= 0:
            max_items = 100
        print(f"[DEBUG] keyword={keyword} max_items={max_items}", flush=True)

        proxy_url = None
        proxy_config = actor_input.get("proxyConfiguration")
        if proxy_config and Actor is not None:
            proxy = await Actor.create_proxy_configuration(
                actor_proxy_input=proxy_config
            )
            if proxy:
                proxy_url = await proxy.new_url()
        print(f"[DEBUG] proxy_url: {proxy_url}", flush=True)

        local_items = []

        async with httpx.AsyncClient(
            timeout=30.0,
            proxies=proxy_url,
            follow_redirects=True,
        ) as client:
            print("[DEBUG] client created", flush=True)
            collected = 0
            page = 1

            while collected < max_items:
                url = f"{BASE_URL}/items?search={quote(keyword)}&page={page}"
                html = await fetch_page(client, url)
                if not html:
                    break

                soup = BeautifulSoup(html, "html.parser")
                items = soup.select("li.item")
                if not items:
                    break

                for li in items:
                    if collected >= max_items:
                        break

                    item = parse_item(li)
                    if item and item.get("productId"):
                        if Actor is not None:
                            await Actor.push_data(item)
                        else:
                            local_items.append(item)
                        collected += 1

                # Stop if fewer than 24 items on the page – likely last page
                if len(items) < 24:
                    break

                page += 1
                await asyncio.sleep(random.uniform(1, 3))

        # Local mode: print JSON list instead of pushing
        if Actor is None:
            print(json.dumps(local_items, ensure_ascii=False, indent=2))
    finally:
        if Actor is not None:
            await Actor.exit()


if __name__ == "__main__":
    asyncio.run(main())
