import yfinance as yf
import pandas as pd  # <--- 이 부분이 빠져 있었습니다. 추가했습니다!
import pandas_ta as ta
import requests
import os
from datetime import datetime

# 환경변수
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TICKERS = ['BTC-USD', 'ETH-USD']

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"전송 실패: {e}")

def check_market_status(ticker):
    # 데이터 가져오기 (주봉, 안전하게 2년치 권장)
    df = yf.download(ticker, period="2y", interval="1wk", progress=False)
    
    # 멀티인덱스 컬럼 처리 (여기서 pd가 사용됩니다)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    # 지표 계산
    df['SMA5'] = ta.sma(df['Close'], length=5)
    df['SMA20'] = ta.sma(df['Close'], length=20)

    # 현재 봉(-1)과 직전 봉(-2) 비교
    current = df.iloc[-1]
    prev = df.iloc[-2]
    
    # ------------------------------------------------------
    # [핵심 로직] 신호 감지
    # ------------------------------------------------------
    signal_msg = None
    
    # 1. 골든 크로스 감지 (어제는 5선이 20선 아래였는데, 오늘은 위로 올라감)
    if prev['SMA5'] <= prev['SMA20'] and current['SMA5'] > current['SMA20']:
        signal_msg = f"🚨 [매수 신호] {ticker} 골든크로스 발생! (진입 추천)"
        
    # 2. 데드 크로스 감지 (어제는 5선이 20선 위였는데, 오늘은 아래로 내려감)
    elif prev['SMA5'] >= prev['SMA20'] and current['SMA5'] < current['SMA20']:
        signal_msg = f"🚨 [매도 신호] {ticker} 데드크로스 발생! (전량 매도 추천)"

    # ------------------------------------------------------
    # [전송 여부 결정]
    # ------------------------------------------------------
    weekday = datetime.today().weekday() # 0:월, 1:화 ... 6:일
    
    if signal_msg:
        # 신호 발생 시 상세 정보 추가
        return f"""
{signal_msg}
현재가: ${current['Close']:,.2f}
SMA 5: {current['SMA5']:,.2f}
SMA 20: {current['SMA20']:,.2f}
"""
    elif weekday == 0:
        # 월요일 정기 보고 (신호 없을 때)
        status = "상승 추세 (보유)" if current['SMA5'] > current['SMA20'] else "하락 추세 (관망)"
        return f"""
📅 [주간 브리핑] {ticker}
상태: {status}
현재가: ${current['Close']:,.2f}
(특이사항 없음)
"""
    else:
        # 신호도 없고 월요일도 아니면 -> 침묵 (None 반환)
        return None

if __name__ == "__main__":
    final_message = "테스트!!!"
    for ticker in TICKERS:
        try:
            msg = check_market_status(ticker)
            if msg: # 메시지가 있을 때만(신호 or 월요일) 추가
                final_message += msg + "\n" + "-"*20 + "\n"
        except Exception as e:
            print(f"Error checking {ticker}: {e}")
            
    # 보낼 메시지가 있을 때만 전송
    if final_message:
        print("메시지 전송함")
        send_telegram_message(final_message)
    else:
        print("보낼 메시지 없음 (특이사항 없음)")