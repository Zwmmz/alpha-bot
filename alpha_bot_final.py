import requests
import schedule
import time
import json
import os
from datetime import datetime, timezone

API_KEY = "4VFHUVAD89JWPSFFZIVP1SPQDR3CAIIE4H"
TELEGRAM_TOKEN = "7854569195:AAE0u8PBYK2BlPICDTRQbg6sNBQyMCnS-jY"
TELEGRAM_CHAT_ID = "864986115"

TOKEN_PRICES = {
    "USDC": 1,
    "BSC-USD": 1,
    "USDT": 1
}

wallets = {
    "寶寶": "0x1f8f53ffef730037ab6a36f0d47548ffe994b2d8",
    "大姐": "0xeb1b7d2dce16c6ef46e18d846be3a9196b580e59",
    "我":   "0xa13f91c8b83b1a6cd7f1322e5e895db0e22b1ea6",
    "二姐": "0x4d09d5e551cff704bf069a2bb43416f50c511c1d",
    "媽媽": "0x8e3a9d5cc3d3511443dc88bd17a3e7bdb8172c11",
    "哥哥": "0x7a1a9669061ed85af6366945e2d5bd6271b81098"
}

def get_bnb_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd"
        response = requests.get(url)
        result = response.json()
        return result["binancecoin"]["usd"]
    except Exception as e:
        print("取得BNB價格失敗:", e)
        return 300

def get_wallet_balance(address):
    url = f"https://api.bscscan.com/api?module=account&action=balance&address={address}&apikey={API_KEY}"
    response = requests.get(url)
    result = response.json()
    return int(result["result"]) / 1e18 if result["status"] == "1" else 0

def calculate_balance_points(balance_usd):
    if balance_usd >= 100000:
        return 4
    elif balance_usd >= 10000:
        return 3
    elif balance_usd >= 1000:
        return 2
    elif balance_usd >= 100:
        return 1
    else:
        return 0

def calculate_volume_points(purchase_usd):
    if purchase_usd < 2:
        return 0
    points = 1
    threshold = 2
    while purchase_usd >= threshold * 2:
        points += 1
        threshold *= 2
    return points

def get_today_received_bnb_internal(address):
    url = f"https://api.bscscan.com/api?module=account&action=txlistinternal&address={address}&startblock=0&endblock=99999999&sort=desc&apikey={API_KEY}"
    response = requests.get(url)
    result = response.json()
    txs = result.get("result")
    if not isinstance(txs, list):
        return 0.0
    today_start = int(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    total_bnb = 0.0
    for tx in txs:
        if int(tx["timeStamp"]) < today_start:
            break
        if tx["to"].lower() == address.lower():
            total_bnb += int(tx["value"]) / 1e18
    return total_bnb

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def load_yesterday_scores():
    if os.path.exists("yesterday_scores.json"):
        with open("yesterday_scores.json", "r") as f:
            return json.load(f)
    return {}

def save_today_scores(today_scores):
    with open("yesterday_scores.json", "w") as f:
        json.dump(today_scores, f)

def update_data():
    print("\n==== 更新中:", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), "====")
    bnb_price = get_bnb_price()
    print(f"BNB 即時價格: ${bnb_price}\n")
    message = f"✅ 每日報告\nBNB 即時價格: ${bnb_price}\n\n"

    yesterday_scores = load_yesterday_scores()
    today_scores = {}

    for nickname, address in wallets.items():
        balance_bnb = get_wallet_balance(address)
        balance_usd = balance_bnb * bnb_price
        balance_points = calculate_balance_points(balance_usd)

        received_bnb_internal = get_today_received_bnb_internal(address)
        trade_volume_usd = received_bnb_internal * bnb_price
        trade_volume_double = trade_volume_usd * 2

        volume_points = calculate_volume_points(trade_volume_double)
        total_points = balance_points + volume_points
        today_scores[address] = total_points

        yesterday = yesterday_scores.get(address, 0)

        message += (
            f"🔹 {nickname} ({address})\n"
            f"   資產估值: ≈ ${balance_usd:,.2f}\n"
            f"   資產積分: {balance_points}\n"
            f"   ➜ 交易量: {received_bnb_internal:.4f} BNB (≈ ${trade_volume_usd:,.2f}) (×2=${trade_volume_double:,.2f})\n"
            f"   交易積分: {volume_points}\n"
            f"   ➜ 總積分: {total_points}\n"
            f"   昨日總積分: {yesterday}\n\n"
        )

    print(message)
    send_telegram_message(message.strip())
    save_today_scores(today_scores)

# 定時排程
schedule.every().day.at("09:00").do(update_data)
schedule.every().day.at("11:00").do(update_data)
schedule.every().day.at("13:00").do(update_data)
schedule.every().day.at("15:00").do(update_data)
schedule.every().day.at("17:00").do(update_data)
schedule.every().day.at("19:00").do(update_data)
schedule.every().day.at("21:00").do(update_data)
schedule.every().day.at("23:00").do(update_data)

update_data()

while True:
    schedule.run_pending()
    time.sleep(1)
