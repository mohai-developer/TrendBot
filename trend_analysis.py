# -*- coding: utf-8 -*-
import yfinance as yf
import pandas as pd
import numpy as np

WATCHLIST = ["MU", "AVGO", "AMD", "NVDA"]

# ==================================================================================
# CLOUD — SMA21 vs SMA34 (نفس Mutanabby)
# ==================================================================================
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

# ==================================================================================
# FRACTALS — نفس منطق HarryBot
# ==================================================================================
def find_fractals(high, low, term=15):
    mid = term // 2 + 1
    n   = len(high)
    frac_highs = []
    frac_lows  = []
    for i in range(mid, n - mid):
        window_h = high.iloc[i - mid : i + mid + 1]
        window_l = low.iloc[i - mid : i + mid + 1]
        if high.iloc[i] == window_h.max():
            frac_highs.append((i, high.iloc[i]))
        if low.iloc[i] == window_l.min():
            frac_lows.append((i, low.iloc[i]))
    return frac_highs, frac_lows

# ==================================================================================
# TRENDLINE SCORE — نفس منطق Metrify
# ==================================================================================
def score_trendline(x1, y1, x2, y2, price, atr, max_slope_deg=6.0, max_rel_atr=8.0):
    dx = max(x2 - x1, 1)
    slope = (y2 - y1) / dx
    safe_atr = max(atr, 1e-10)
    y_now = y1 + slope * (x2 - x1)
    rel_dist = abs(price - y_now)
    max_rel = safe_atr * max_rel_atr
    max_slope = np.tan(max_slope_deg * np.pi / 180.0)
    slope_atr = abs(slope) / safe_atr
    if rel_dist > max_rel or slope_atr > max_slope:
        return -999.0
    recency  = 1.0
    tightness = 1.0 - min(rel_dist / (safe_atr * 0.3), 1.0)
    return recency * 1.2 + tightness * 1.3 - slope_atr * 0.5

# ==================================================================================
# TRENDLINE STATUS — يبحث عن أفضل خط بين الـ Fractals
# ==================================================================================
def get_trendline_status(high, low, close, term=15, segment=55):
    price  = close.iloc[-1]
    atr    = (high - low).rolling(14).mean().iloc[-1]
    n      = len(close)

    frac_highs, frac_lows = find_fractals(high, low, term)

    # --- خط المقاومة: أفضل خط من Fractal Highs ---
    best_res_score = -999.0
    best_res       = None
    if len(frac_highs) >= 2:
        for i in range(len(frac_highs) - 1, max(len(frac_highs) - segment, 0) - 1, -1):
            x2, y2 = frac_highs[i]
            x1, y1 = frac_highs[i - 1] if i > 0 else frac_highs[i]
            if x2 == x1:
                continue
            sc = score_trendline(x1, y1, x2, y2, price, atr)
            if sc > best_res_score:
                best_res_score = sc
                best_res = (x1, y1, x2, y2)

    # --- خط الدعم: أفضل خط من Fractal Lows ---
    best_sup_score = -999.0
    best_sup       = None
    if len(frac_lows) >= 2:
        for i in range(len(frac_lows) - 1, max(len(frac_lows) - segment, 0) - 1, -1):
            x2, y2 = frac_lows[i]
            x1, y1 = frac_lows[i - 1] if i > 0 else frac_lows[i]
            if x2 == x1:
                continue
            sc = score_trendline(x1, y1, x2, y2, price, atr)
            if sc > best_sup_score:
                best_sup_score = sc
                best_sup = (x1, y1, x2, y2)

    # --- حساب سعر الخط الحالي ---
    def line_price_now(x1, y1, x2, y2):
        slope = (y2 - y1) / max(x2 - x1, 1)
        return y1 + slope * (n - 1 - x1)

    res_price = line_price_now(*best_res) if best_res else None
    sup_price = line_price_now(*best_sup) if best_sup else None

    # --- تحديد القوة ---
    res_strong = best_res_score > 0.5 if best_res else False
    sup_strong = best_sup_score > 0.5 if best_sup else False

    # --- تحديد الاتجاه ---
    res_dist = abs(price - res_price) if res_price else float('inf')
    sup_dist = abs(price - sup_price) if sup_price else float('inf')

    approaching_res = res_price and price < res_price and res_dist < atr * 2
    approaching_sup = sup_price and price > sup_price and sup_dist < atr * 2
    broke_res       = res_price and price > res_price
    broke_sup       = sup_price and price < sup_price

    if approaching_res:
        direction = "يقترب من خط مقاومة"
        line_type = "مقاومة"
        strength  = "قوي" if res_strong else "ضعيف"
        line_val  = res_price
    elif broke_res:
        direction = "اخترق صعوداً خط مقاومة"
        line_type = "مقاومة"
        strength  = "قوي" if res_strong else "ضعيف"
        line_val  = res_price
    elif approaching_sup:
        direction = "يتراجع نحو خط دعم"
        line_type = "دعم"
        strength  = "قوي" if sup_strong else "ضعيف"
        line_val  = sup_price
    elif broke_sup:
        direction = "كسر هبوطاً خط دعم"
        line_type = "دعم"
        strength  = "قوي" if sup_strong else "ضعيف"
        line_val  = sup_price
    else:
        # السعر بين الخطين
        direction = "يتداول بين الدعم والمقاومة"
        line_type = "دعم ومقاومة"
        strength  = "قوي" if (res_strong and sup_strong) else "ضعيف"
        line_val  = (res_price + sup_price) / 2 if res_price and sup_price else price

    return direction, line_type, strength, round(line_val, 2) if line_val else None

# ==================================================================================
# TARGETS — TP1 TP2 TP3 بناءً على ATR (نفس Mutanabby)
# ==================================================================================
def get_targets(close, high, low, direction):
    price   = close.iloc[-1]
    atr     = (high - low).rolling(14).mean().iloc[-1]
    is_bull = "اخترق" in direction or "صعود" in direction

    if is_bull:
        sl  = round(price - atr, 2)
        tp1 = round(price + atr * 1, 2)
        tp2 = round(price + atr * 2, 2)
        tp3 = round(price + atr * 3, 2)
    else:
        sl  = round(price + atr, 2)
        tp1 = round(price - atr * 1, 2)
        tp2 = round(price - atr * 2, 2)
        tp3 = round(price - atr * 3, 2)

    return {"sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3}

# ==================================================================================
# VOLUME
# ==================================================================================
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

# ==================================================================================
# RECOMMENDATION
# ==================================================================================
def get_recommendation(direction, strength, cloud_bullish, cloud_phase, volume_status):
    bullish_signal = "اخترق" in direction or "صعود" in direction
    bearish_signal = "كسر" in direction or "هبوط" in direction or "تراجع" in direction
    strong    = strength == "قوي"
    vol_good  = volume_status in ["قوي", "متوسط"]
    cloud_ok  = (bullish_signal and cloud_bullish) or (bearish_signal and not cloud_bullish)
    score = 0
    if strong:   score += 2
    if vol_good: score += 1
    if cloud_ok: score += 2
    if "بداية تكون" in cloud_phase and cloud_ok: score += 1
    if score >= 4:
        return "احتمال قوي لاستمرار الاتجاه"
    elif score >= 2:
        return "اتجاه محتمل مع الحذر"
    else:
        return "تذبذب بدون اتجاه واضح"

# ==================================================================================
# MAIN ANALYZER
# ==================================================================================
def analyze_ticker(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 50:
            return None
        close  = df["Close"].squeeze()
        high   = df["High"].squeeze()
        low    = df["Low"].squeeze()
        volume = df["Volume"].squeeze()
        last_date = df.index[-1].strftime("%Y-%m-%d")
        timeframe = "Daily (1D)"

        cloud_bullish, cloud_phase  = get_cloud_status(close)
        direction, line_type, strength, line_val = get_trendline_status(high, low, close)
        volume_status               = get_volume_status(volume)
        recommendation              = get_recommendation(direction, strength, cloud_bullish, cloud_phase, volume_status)
        targets                     = get_targets(close, high, low, direction)
        cloud_color                 = "خضراء" if cloud_bullish else "حمراء"
        price                       = round(float(close.iloc[-1]), 2)

        return {
            "ticker":         ticker,
            "price":          price,
            "direction":      direction,
            "line_type":      line_type,
            "line_val":       line_val,
            "strength":       strength,
            "cloud_color":    cloud_color,
            "cloud_phase":    cloud_phase,
            "volume_status":  volume_status,
            "recommendation": recommendation,
            "targets":        targets,
            "last_date":      last_date,
            "timeframe":      timeframe
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
