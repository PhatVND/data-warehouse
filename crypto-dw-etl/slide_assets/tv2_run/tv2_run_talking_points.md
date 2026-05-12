# TV2 Cleaning Run - Talking Points

- Da doc 10 file raw CSV trong folder `raw/`.
- Tong so dong dau vao: 7300.
- Sau khi ap dung cleaning rules cua TV2, so dong hop le: 7300.
- So dong bi ghi vao reject log: 0.
- Sau clean, so symbol hop le: 10 (ADA, BNB, BTC, DOGE, DOT, ETH, MATIC, SOL, TRX, XRP).
- Check sau clean:
  - `high < low`: 0
  - `volume < 0`: 0
  - symbol con suffix `USDT`: 0
  - duplicate `(symbol, open_time)`: 0

Ket luan bao cao:
Batch raw hien tai sach nen khong phat sinh reject. Tuy nhien TV2 van can cleaning job vi pipeline hang ngay co the gap du lieu loi, duplicate hoac format moi tu source.
