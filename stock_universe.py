"""
Stock universe — 129 active stocks from Finviz screener.
Filters: avg_vol>750K, price>15, beta>1, price near/above MA50.
All verified active as of March 2025.
"""

STOCK_UNIVERSE = [
    # 1-20
    "AAOI", "ABVX", "ADEA", "AEHR", "AL", "AMAT", "AMPX", "ARM",
    "ASX", "ATEN", "AXTI", "BFH", "BKSY", "BKV", "BRX", "BSY",
    "BTSG", "BURL", "BW", "BWIN",
    # 21-40
    "CARG", "CAVA", "CC", "CGNX", "CIEN", "CLDX", "CLMT", "CNK",
    "CNTA", "COHR", "COHU", "COIN", "CRC", "CVI", "CZR", "DAR",
    "DDOG", "DFTX", "DLR", "DNLI",
    # 41-60
    "DNTH", "DOCN", "DYN", "ENPH", "EXAS", "FDX", "FIVE", "FORM",
    "FTNT", "GEV", "GLDD", "GLW", "GNRC", "GPRE", "GUSH", "GWRE",
    "ICHR", "INGM", "IOT", "JBL",
    # 61-80
    "JCI", "JHG", "KEYS", "KIM", "KLAC", "KRMN", "KTB", "LASR",
    "LITE", "LRCX", "MASI", "MOD", "MRNA", "MRVL", "MTZ", "MU",
    "MUU", "NBIS", "NE", "NET",
    # 81-100
    "NFLX", "NFXL", "NSA", "NTAP", "NVT", "NXT", "NYT", "OII",
    "OS", "OUT", "PARR", "PL", "PLAB", "POWI", "PWR", "RNG",
    "ROIV", "RSI", "SDRL", "SEDG",
    # 101-120
    "SEE", "SEI", "SEM", "SNDK", "SPHR", "SRAD", "STX", "TER",
    "TGT", "TGTX", "TNDM", "TNGX", "TPH", "TWLO", "UCTT", "UE",
    "VAL", "VG", "VRE", "VRT",
    # 121-129
    "VSAT", "WDC", "WIX", "WULF", "XPO", "YOU", "YPF", "ZD", "ZIM",
]
