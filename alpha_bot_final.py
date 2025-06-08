import requests
import schedule
import time
from datetime import datetime
import pytz

API_KEY = "4VFHUVAD89JWPSFFZIVP1SPQDR3CAIIE4H"
TELEGRAM_TOKEN = "7854569195:AAE0u8PBYK2BlPICDTRQbg6sNBQyMCnS-jY"
TELEGRAM_CHAT_ID = "864986115"

wallets = {
    "寶寶": "0x1f8f53ffef730037ab6a36f0d47548ffe994b2d8",
    "大姐": "0xeb1b7d2dce16c6ef46e18d846be3a9196b580e59",
    "我":   "0xa13f91c8b83b1a6cd7f1322e5e895db0e22b1ea6",
    "二姐": "0x4d09d5e551cff704bf069a2bb43416f50c511c1d",
    "媽媽": "0x8e3a9d5cc3d3511443dc88bd17a3e7bdb8172c11",
    "哥哥": "0x7a1a9669061ed85af6366945e2d5bd6271b81098"
}

# 新增要查詢的兩個代幣
TOKENS = {
    "幣種A": "0xe6df05ce8c8301223373cf5b969afcb1498c5528",
    "幣種B": "0xc71b5f631354be6853efe9c3ab6b9590f8302e81"
}

def get_bnb_price():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd"
    response = requests.get(url)
    return response.json().get("binancecoin", {}).get("usd", 300)

def get_token_price(contract_address):
    url = f"https://api.coingecko.com/api/v3/simple/token_price/binance-smart-chain?contract_addresses={contract_address}&vs_currencies=usd"
    response = requests.get(url)
    result = response.json()
    return list(result.values())[0]["usd"] if result else 0

def get_token_balance(address, contract_address):
    url = f"https://api.bscscan.com/api?module=account&action=tokenbalance&contractaddress={contract_address}&address={address}&apikey={API_KEY}"
    response = requests.get(url)
    return int(response.json().get("result", 0)) / 1e18

def get_wallet_balance(address):
    url = f"https://api.bscscan.com/api?module=account&action=balance&address={address}&apikey={API_KEY}"
    response = requests.get(url)
    return int(response.json().get("result", 0)) / 1e18

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
    txs = response.json().get("result", [])
    taiwan_tz = pytz.timezone("Asia/Taipei")
    today_start = int(datetime.now(taiwan_tz).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc).timestamp())
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

def update_data():
    taiwan_tz = pytz.timezone("Asia/Taipei")
    current_time = datetime.now(taiwan_tz).strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n==== 更新中 (台灣時間): {current_time} ====")

    bnb_price = get_bnb_price()
    tokenA_price = get_token_price(TOKENS["幣種A"])
    tokenB_price = get_token_price(TOKENS["幣種B"])

    message = f"✅ 報告時間: {current_time} (台灣時間)\nBNB 即時價格: ${bnb_price}\n\n"

    for nickname, address in wallets.items():
        # BNB
        balance_bnb = get_wallet_balance(address)
        balance_usd_bnb = balance_bnb * bnb_price

        # 幣種 A
        balance_tokenA = get_token_balance(address, TOKENS["幣種A"])
        balance_usd_tokenA = balance_tokenA * tokenA_price

        # 幣種 B
        balance_tokenB = get_token_balance(address, TOKENS["幣種B"])
        balance_usd_tokenB = balance_tokenB * tokenB_price

        # 總資產估值
        total_balance_usd = balance_usd_bnb + balance_usd_tokenA + balance_usd_tokenB
        balance_points = calculate_balance_points(total_balance_usd)

        # 當日交易
        received_bnb = get_today_received_bnb_internal(address)
        trade_usd = received_bnb * bnb_price
        trade_double = trade_usd * 2
        volume_points = calculate_volume_points(trade_double)

        total_points = balance_points + volume_points

        message += (
            f"🔹 {nickname} ({address})\n"
            f"   BNB: {balance_bnb:.4f} ≈ ${balance_usd_bnb:,.2f}\n"
            f"   幣種A: {balance_tokenA:.4f} ≈ ${balance_usd_tokenA:,.2f}\n"
            f"   幣種B: {balance_tokenB:.4f} ≈ ${balance_usd_tokenB:,.2f}\n"
            f"   ➜ 總資產估值: ${total_balance_usd:,.2f}\n"
            f"   資產積分: {balance_points}\n"
            f"   ➜ 交易量: {received_bnb:.4f} BNB (≈ ${trade_usd:,.2f}) (×2=${trade_double:,.2f})\n"
            f"   交易積分: {volume_points}\n"
            f"   ➜ 總積分: {total_points}\n\n"
        )

    print(message)
    send_telegram_message(message.strip())

# 定時排程 (台灣時間)
schedule.every().day.at("10:00").do(update_data)
schedule.every().day.at("13:00").do(update_data)
schedule.every().day.at("16:00").do(update_data)
schedule.every().day.at("20:00").do(update_data)
schedule.every().day.at("23:00").do(update_data)

update_data()  # 啟動時立刻執行一次

while True:
    schedule.run_pending()
    time.sleep(1)
