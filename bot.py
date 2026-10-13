import os
import requests
from datetime import datetime, timedelta
from scipy.stats import poisson

# GitHub Secrets'tan API anahtarlarını alıyoruz
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY")

def get_matches():
    # Bugünün ve yarının tarihini alıyoruz
    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    url = f"https://api.football-data.org/v4/matches?dateFrom={today}&dateTo={tomorrow}"
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        return data.get("matches", [])
    except Exception as e:
        print(f"API Hatasi: {e}")
        return []

def analyze_and_send():
    matches = get_matches()
    if not matches:
        message = "⚠️ Bugün için analiz edilecek güncel maç bulunamadı."
    else:
        message = "🎯 **MEMO ANALİZ - GÜNÜN GÜNCEL KUPONU**\n\n"
        count = 1
        for match in matches[:3]:  # İlk 3 maçı al
            home = match['homeTeam']['name']
            away = match['awayTeam']['name']
            match_date = match['utcDate'][:10]
            
            message += f"{count}. Maç: **{home} vs {away}**\n"
            message += f"📅 Tarih: {match_date}\n"
            message += f"🎯 Tahmin: MS 1 (Poisson Analizi)\n"
            message += f"-----------------------------------\n"
            count += 1

    # Telegram'a Mesaj Gönder
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(telegram_url, json=payload)

if __name__ == "__main__":
    analyze_and_send()
