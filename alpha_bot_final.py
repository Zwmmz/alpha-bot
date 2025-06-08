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

TOKENS = {
    "KEGO": "0xe6df05ce8c8301223373cf5b969afcb1498c5528",
    "ZKJ": "0xc71b5f631354be6853efe9c3ab6b9590f8302e81"
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

def get_wallet_balance(address):
    url = f"https://api.bscscan.com/api?module=account&action=balance&address={address}&apikey={API_KEY}"
    response = requests.get(url)
    return int(response.json().get("result", 0)) / 1e18

def get_token_balance(address, contract_address):
    url = f"https://api.bscscan.com/api?module=account&action=tokenbalance&contractaddress={contract_address}&address={address}&apikey={API_KEY}"
    response = requests.get(url)
    return int(response.json().get("result", 0)) / 1e18

def get_today_sent_token(address, token_address):
    # 排除 BNB Swap Pool 合約地址（例如 WBNB）
    bnb_swap_pools = ["0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"]
    url = f"https://api.bscscan.com/api?module=account&action=tokentx&contractaddress={token_address}&address={address}&startblock=0&endblock=99999999&sort=desc&apikey={API_KEY}"
    response = requests.get(url)
    txs = response.json().get("result", [])
    taiwan_tz = pytz.timezone("Asia/Taipei")
    today_start = int(datetime.now(taiwan_tz).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc).timestamp())
    total = 0.0
    for tx in txs:
        if int(tx["timeStamp"]) < today_start:
            break
        if tx["from"].lower() == address.lower():
            if tx["to"].lower() in bnb_swap_pools:
                continue
            total += int(tx["value"]) / (10 ** int(tx["tokenDecimal"]))
    return total

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

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def update_data():
    taiwan_tz = pytz.timezone("Asia/Taipei")
    current_time = datetime.now(taiwan_tz).strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n==== 更新中 (台灣時間): {current_time} ====")

    bnb_price = get_bnb_price()
    kego_price = get_token_price(TOKENS["KEGO"])
    zkj_price = get_token_price(TOKENS["ZKJ"])

    message = f"✅ 報告時間: {current_time} (台灣時間)\nBNB 即時價格: ${bnb_price}\n\n"

    for nickname, address in wallets.items():
        balance_bnb = get_wallet_balance(address)
        balance_usd_bnb = balance_bnb * bnb_price

        balance_kego = get_token_balance(address, TOKENS["KEGO"])
        balance_usd_kego = balance_kego * kego_price

        balance_zkj = get_token_balance(address, TOKENS["ZKJ"])
        balance_usd_zkj = balance_zkj * zkj_price

        total_balance_usd = balance_usd_bnb + balance_usd_kego + balance_usd_zkj
        balance_points = calculate_balance_points(total_balance_usd)

        received_bnb = get_today_received_bnb_internal(address)
        trade_usd = received_bnb * bnb_price

        sent_kego = get_today_sent_token(address, TOKENS["KEGO"])
        sent_zkj = get_today_sent_token(address, TOKENS["ZKJ"])
        sent_kego_usd = sent_kego * kego_price
        sent_zkj_usd = sent_zkj * zkj_price

        total_trade_usd = trade_usd + sent_kego_usd + sent_zkj_usd
        trade_double = total_trade_usd * 2
        volume_points = calculate_volume_points(trade_double)
        total_points = balance_points + volume_points

        message += (
            f"🔹 {nickname} ({address})\n"
            f"   ➜ BNB: {balance_bnb:.4f} ≈ ${balance_usd_bnb:,.2f}\n"
            f"   ➜ KEGO: {balance_kego:.4f} ≈ ${balance_usd_kego:,.2f}\n"
            f"   ➜ ZKJ: {balance_zkj:.4f} ≈ ${balance_usd_zkj:,.2f}\n"
            f"   ➜ 總資產估值: ${total_balance_usd:,.2f}\n"
            f"   ➜ 交易量 BNB: {received_bnb:.4f} (≈ ${trade_usd:,.2f})\n"
            f"   ➜ 交易量 KEGO: {sent_kego:.4f} (≈ ${sent_kego_usd:,.2f})\n"
            f"   ➜ 交易量 ZKJ: {sent_zkj:.4f} (≈ ${sent_zkj_usd:,.2f})\n"
            f"   ➜ 總交易量(USD)×2: ${trade_double:,.2f}\n"
            f"   ➜ 資產積分: {balance_points}\n"
            f"   ➜ 交易積分: {volume_points}\n"
            f"   ➜ 總積分: {total_points}\n\n"
        )

    print(message)
    send_telegram_message(message.strip())

# 每 2 小時報告
schedule.every(2).hours.do(update_data)
update_data()  # 啟動時執行一次

while True:
    schedule.run_pending()
    time.sleep(1)
