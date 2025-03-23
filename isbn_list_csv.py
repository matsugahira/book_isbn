#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import csv
import uuid
import logging
import time
import requests

# ---------------------------
# カスタムログフォーマッターの定義
# ---------------------------
class CustomFormatter(logging.Formatter):
    # formatTimeをオーバーライドしてミリ秒まで表示する
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
            # record.msecsはミリ秒
            return f"{s},{int(record.msecs):03d}"
        else:
            t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
            return f"{t},{int(record.msecs):03d}"

# ---------------------------
# UUIDの生成と設定
# ---------------------------
# スクリプト実行時にUUIDを生成し、先頭8桁を共通識別子として利用する
common_uuid = str(uuid.uuid4())[:8]

# ---------------------------
# ロガーの設定
# ---------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stderr)
# ログフォーマットの設定（メッセージ内に共通UUIDを含める）
formatter = CustomFormatter(fmt=f"%(asctime)s - %(levelname)s - {common_uuid} - %(message)s",
                              datefmt="%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)

# ---------------------------
# ISBN情報取得関数の定義
# ---------------------------
def fetch_book_info(isbn):
    """
    ISBNをもとにOpenBD APIから書籍情報を取得する関数。
    正常時は (title, publisher, PriceAmount) のタプルを返す。
    エラー時は空文字列を返す。
    """
    api_url = f"https://api.openbd.jp/v1/get?isbn={isbn}"
    try:
        # APIリクエスト送信
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()  # HTTPエラーがあれば例外を発生させる
    except Exception as e:
        logger.error(f"Error fetching data for ISBN {isbn}: {e}")
        return ("", "", "")
    
    try:
        data = response.json()
        # dataがリストで、かつ最初の要素が None でないことを確認
        if not data or data[0] is None:
            logger.error(f"No data found for ISBN {isbn}")
            return ("", "", "")
        
        # 各アトリビュートの抽出
        title = data[0]["onix"]["DescriptiveDetail"]["TitleDetail"]["TitleElement"]["TitleText"]["content"]
        publisher = data[0]["onix"]["PublishingDetail"]["Imprint"]["ImprintName"]
        # Priceはリストの先頭要素を使用する
        price = data[0]["onix"]["ProductSupply"]["SupplyDetail"]["Price"][0]["PriceAmount"]
        return (title, publisher, price)
    except Exception as e:
        logger.error(f"Error parsing data for ISBN {isbn}: {e}")
        return ("", "", "")

# ---------------------------
# メイン処理
# ---------------------------
def main():
    # コマンドライン引数の確認
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python isbn_list_csv.py input.csv\n")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    
    # 結果を保持するリスト（ヘッダー行も含む）
    output_rows = []
    header = ["isbn", "title", "publisher", "PriceAmount"]
    output_rows.append(header)
    
    try:
        # 入力CSVファイルのオープン
        with open(input_csv, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            first_row = next(reader)
            # ヘッダーが存在するかどうかの簡易判定（ISBNが数字のみの場合を想定）
            if first_row and first_row[0].strip().lower() in ["isbn", "id"]:
                # ヘッダー行なのでスキップ
                pass
            else:
                # ヘッダーではなかった場合は先頭行も処理対象に含める
                process_row = first_row
                isbn = process_row[0].strip()
                logger.info(f"ISBN {isbn}: Processing started")
                title, publisher, price = fetch_book_info(isbn)
                output_rows.append([isbn, title, publisher, price])
            
            # 残りの行を処理
            for row in reader:
                if not row:
                    continue
                isbn = row[0].strip()
                logger.info(f"ISBN {isbn}: Processing started")
                title, publisher, price = fetch_book_info(isbn)
                output_rows.append([isbn, title, publisher, price])
    except Exception as e:
        logger.error(f"Error reading input CSV: {e}")
        sys.exit(1)
    
    # CSV出力（標準出力へ、改行コードはLF固定）
    writer = csv.writer(sys.stdout, lineterminator="\n")
    for row in output_rows:
        writer.writerow(row)

if __name__ == "__main__":
    main()
