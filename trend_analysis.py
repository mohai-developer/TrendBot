# -*- coding: utf-8 -*-
import yfinance as yf
import pandas as pd
import numpy as np

WATCHLIST = ["MU", "AVGO", "AMD", "NVDA"]

def get_cloud_status(close):
    sma21 = close.rolling(21).mean()
    sma34 = close.rolling(34).mean()
    curr21 = sma21.iloc[-1]
    curr34 = sma34.iloc[-1]
    prev21 = sma21.iloc[-2]
    prev34 = sma34.iloc[-2]
    bullish = curr21 > curr34
    just_crossed = (curr21 > curr34) != (prev21 > prev34)
    gap = abs(curr21 - curr34) / curr34 * 100
    if just_crossed:
        phase = "بداية تكون"
    elif gap < 0.3:
        phase = "اقتراب انتهاء"
    else:
        phase = "مستمرة"
    return bullish, phase

def get_trendline_status(high, low, close, term=15):
    mid = term // 2 + 1
    resistance = high.rolling(term).max().iloc[-mid]
    support    = low.rolling(term).min().iloc[-mid]
    price      = close.iloc[-1]
    atr        = (high - low).rolling(14).mean().iloc[-1]
    max_rel    = atr * 8.0
    res_dist = abs(price - resistance)
    sup_dist = abs(price - support)
    res_strong = res_dist <= max_rel
    sup_strong = sup_dist <= max_rel
    approaching_res = res_dist < atr * 2 and price < resistance
    approaching_sup = sup_dist < atr * 2 and price > support
    if approaching_res:
        direction = "يقترب من خط مقاومة"
        line_type = "مقاومة"
        strength  = "قوي" if res_strong else "ضعيف"
    elif approaching_sup:
        direction = "يتراجع نحو خط دعم"
        line_type = "دعم"
        strength  = "قوي" if sup_strong else "ضعيف"
    elif price > resistance:
        direction = "اخترق صعوداً خط مقاومة"
        line_type = "مقاومة"
        strength  = "قوي" if res_strong else "ضعيف"
    else:
        direction = "كسر هبوطاً خط دعم"
        line_type = "دعم"
        strength  = "قوي" if sup_strong else "ضعيف"
    return direction, line_type, strength

def get_volume_status(volume):
    avg20 = volume.rolling(20).mean().iloc[-1]
    curr  = volume.iloc[-1]
    ratio = curr / avg20
    if ratio >= 1.5:
        return "قوي"
    elif ratio >= 0.8:
        return "متوسط"
    else:
        return "ضعيف"

def get_recommendation(direction, strength, cloud_bullish, cloud_phase, volume_status):
    bullish_signal = "صعود" in direction or "اخترق" in direction
    bearish_signal = "هبوط" in direction or "كسر" in direction or "تراجع" in direction
    strong = strength == "قوي"
    vol_good = volume_status in ["قوي", "متوسط"]
    cloud_confirming = (bullish_signal and cloud_bullish) or (bearish_signal and not cloud_bullish)
    score = 0
    if strong: score += 2
    if vol_good: score += 1
    if cloud_confirming: score += 2
    if "بداية تكون" in cloud_phase and cloud_confirming: score += 1
    if score >= 4:
        return "احتمال قوي لاستمرار الاتجاه"
    elif score >= 2:
        return "اتجاه محتمل مع الحذر"
    else:
        return "تذبذب بدون اتجاه واضح"

def analyze_ticker(ticker):
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 35:
            return None
        close  = df["Close"].squeeze()
        high   = df["High"].squeeze()
        low    = df["Low"].squeeze()
        volume = df["Volume"].squeeze()
        last_date = df.index[-1].strftime("%Y-%m-%d")
        timeframe = "Daily (1D)"
        cloud_bullish, cloud_phase = get_cloud_status(close)
        direction, line_type, strength = get_trendline_status(high, low, close)
        volume_status = get_volume_status(volume)
        recommendation = get_recommendation(direction, strength, cloud_bullish, cloud_phase, volume_status)
        cloud_color = "خضراء" if cloud_bullish else "حمراء"
        return {
            "ticker": ticker,
            "direction": direction,
            "line_type": line_type,
            "strength": strength,
            "cloud_color": cloud_color,
            "cloud_phase": cloud_phase,
            "volume_status": volume_status,
            "recommendation": recommendation,
            "last_date": last_date,
            "timeframe": timeframe
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}

def run_analysis():
    results = []
    for ticker in WATCHLIST:
        result = analyze_ticker(ticker)
        if result:
            results.append(result)
    return results