import os
import requests
from scipy.stats import poisson

# --- GÜVENLİ ENVIRONMENT/SECRETS ALIMI ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8870185295:AAF-hK9f_SuTJj5-39ArTge19kiTrfHnsXs")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1004358479111")
FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_KEY", "c1de17f8bc384f198dd43a3d7bcf94a6")
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "7dbc85f00bda76339612550c6d013314")
THESPORTSDB_KEY = "123"

def telegram_bildir(mesaj):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram hatası: {e}")

def poisson_25_analiz(ev_xg, dep_xg):
    toplam_25_alti = 0
    for ev_gol in range(3):
        for dep_gol in range(3 - ev_gol):
            p_ev = poisson.pmf(ev_gol, ev_xg)
            p_dep = poisson.pmf(dep_gol, dep_xg)
            toplam_25_alti += p_ev * p_dep
    return round((1 - toplam_25_alti) * 100, 1)

def poisson_1x2_analiz(ev_xg, dep_xg):
    p_ev_kazanir = 0
    p_beraberlik = 0
    p_dep_kazanir = 0
    
    for ev_gol in range(7):
        for dep_gol in range(7):
            p = poisson.pmf(ev_gol, ev_xg) * poisson.pmf(dep_gol, dep_xg)
            if ev_gol > dep_gol:
                p_ev_kazanir += p
            elif ev_gol == dep_gol:
                p_beraberlik += p
            else:
                p_dep_kazanir += p
                
    return round(p_ev_kazanir * 100, 1), round(p_beraberlik * 100, 1), round(p_dep_kazanir * 100, 1)

def gunun_akilli_kuponunu_uret():
    print("🎯 Bülten taranıyor, maçlar analiz ediliyor...")
    
    # 1. Oranları çekelim
    odds_url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=totals&oddsFormat=decimal"
    oran_sozlugu = {}
    try:
        odds_resp = requests.get(odds_url, timeout=10)
        if odds_resp.status_code == 200:
            for game in odds_resp.json():
                home, away = game.get("home_team"), game.get("away_team")
                bookmakers = game.get("bookmakers", [])
                if bookmakers:
                    for market in bookmakers[0].get("markets", []):
                        if market.get("key") == "totals":
                            for out in market.get("outcomes", []):
                                if out.get("name") == "Over" and out.get("point") == 2.5:
                                    oran_sozlugu[(home, away)] = out.get("price")
    except Exception as e:
        print(f"Oran çekme uyarısı: {e}")

    # 2. football-data.org istatistikleri
    lig_tabelasi_xg = {}
    fd_url = "https://api.football-data.org/v4/competitions/PL/standings"
    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    
    try:
        fd_resp = requests.get(fd_url, headers=headers, timeout=10)
        if fd_resp.status_code == 200:
            standings = fd_resp.json().get("standings", [])[0].get("table", [])
            for team_info in standings:
                team_name = team_info.get("team", {}).get("name")
                played = team_info.get("playedGames", 1)
                goals_for = team_info.get("goalsFor", 0)
                goals_against = team_info.get("goalsAgainst", 0)
                
                mac_basi_atan = goals_for / max(played, 1)
                mac_basi_yeyen = goals_against / max(played, 1)
                lig_tabelasi_xg[team_name] = {"atan": mac_basi_atan, "yeyen": mac_basi_yeyen}
    except Exception as e:
        print(f"Football-data istatistik uyarısı: {e}")

    # 3. Maç taraması
    sportsdb_url = f"https://www.thesportsdb.com/api/v1/json/{THESPORTSDB_KEY}/eventsround.php?id=4328&r=38&s=2024-2025"
    
    aday_maclar = []
    try:
        resp = requests.get(sportsdb_url, timeout=10)
        storage = resp.json()
        events = storage.get("events")
        
        if events:
            for event in events:
                ev = event.get("strHomeTeam", "Ev Sahibi")
                dep = event.get("strAwayTeam", "Deplasman")
                tarih = event.get("dateEvent", "N/A")
                saat = event.get("strTime", "N/A")
                
                iddaa_orani = oran_sozlugu.get((ev, dep), 1.85)
                
                ev_stats = lig_tabelasi_xg.get(ev, {"atan": 1.4, "yeyen": 1.1})
                dep_stats = lig_tabelasi_xg.get(dep, {"atan": 1.2, "yeyen": 1.4})
                
                ev_xg = round((ev_stats["atan"] + dep_stats["yeyen"]) / 2, 2)
                dep_xg = round((dep_stats["atan"] + ev_stats["yeyen"]) / 2, 2)
                
                ms1_ihtimal, x_ihtimal, ms2_ihtimal = poisson_1x2_analiz(ev_xg, dep_xg)
                
                en_yuksek_1x2 = max(ms1_ihtimal, x_ihtimal, ms2_ihtimal)
                if en_yuksek_1x2 == ms1_ihtimal:
                    tahmin_str = f"MS 1 (%{ms1_ihtimal})"
                    guven_skoru = ms1_ihtimal
                elif en_yuksek_1x2 == ms2_ihtimal:
                    tahmin_str = f"MS 2 (%{ms2_ihtimal})"
                    guven_skoru = ms2_ihtimal
                else:
                    tahmin_str = f"X - Beraberlik (%{x_ihtimal})"
                    guven_skoru = x_ihtimal

                aday_maclar.append({
                    "ev": ev,
                    "dep": dep,
                    "tarih": tarih,
                    "saat": saat,
                    "tahmin": tahmin_str,
                    "guven": guven_skoru,
                    "oran": iddaa_orani
                })
            
            aday_maclar.sort(key=lambda x: x["guven"], reverse=True)
            en_iyi_maclar = aday_maclar[:3]
            
            kupon_mesaji = "🎟️ *MEMO ANALİZ - GÜNÜN AKILLI KUPONU*\n\n"
            toplam_oran_tahmini = 1.0
            
            for i, mac in enumerate(en_iyi_maclar, 1):
                kupon_mesaji += (
                    f"*{i}. Maç:* {mac['ev']} vs {mac['dep']}\n"
                    f"📅 {mac['tarih']} | 🕒 {mac['saat']}\n"
                    f"🎯 *Tahmin:* {mac['tahmin']} (Güven: %{mac['guven']})\n"
                    f"💰 *Oran:* {mac['oran']}\n"
                    f"-----------------------------------\n"
                )
                toplam_oran_tahmini *= float(mac['oran'])
            
            kupon_mesaji += f"🔥 *Önerilen Kombine Oranı:* {round(toplam_oran_tahmini, 2)}\n"
            kupon_mesaji += "⚡ *Strateji:* Maç Öncesi Saf Matematiksel Filtreleme"
            
            telegram_bildir(kupon_mesaji)
            print("📩 Kupon Telegram'a başarıyla gönderildi!")
            
        else:
            telegram_bildir("🤖 *MemoAnalizBot:* Bültende uygun maç bulunamadı.")
            
    except Exception as e:
        print(f"Bağlantı Hatası: {e}")

if __name__ == "__main__":
    gunun_akilli_kuponunu_uret()
