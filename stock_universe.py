"""
Stock universe — cleaned, active US stocks only (March 2025).
Removed all delisted/acquired tickers.
"""

FINVIZ_PICKS = [
    "AAOI", "AEHR", "AMPX", "AXTI", "BE", "BKSY", "CC", "CNTA", "COHR",
    "COIN", "DOCN", "HIMS", "ICHR", "LASR", "NBIS", "PL", "SNDK",
    "SRAD", "STX", "TGTX", "TNDM", "UCTT", "UMAC", "WDC", "WULF",
]

STOCK_UNIVERSE = list(dict.fromkeys(FINVIZ_PICKS + [
    # Financials
    "GS", "MS", "JPM", "BAC", "WFC", "C", "AXP", "COF", "DFS", "SYF",
    "BK", "STT", "SCHW", "HOOD", "ICE", "CME", "CBOE", "ALLY",
    "RF", "CFG", "HBAN", "KEY", "MTB", "USB", "PNC", "CMA", "FITB",
    "BX", "KKR", "APO", "ARES", "CG", "TROW", "IVZ", "BEN", "AMG",
    "MET", "PRU", "AFL", "AIG", "HIG", "TRV", "CB", "ALL", "PGR",
    "CINF", "WRB", "RE", "RNR", "AIZ", "GL", "UNM", "FNF", "FAF",

    # Technology
    "IBM", "HPQ", "HPE", "DELL", "CDW", "NTAP", "STX", "WDC",
    "AMAT", "LRCX", "KLAC", "MCHP", "SWKS", "QRVO", "MPWR",
    "FSLR", "ENPH", "ON", "WOLF", "AMBA", "SITM",
    "CRUS", "PLAB", "ONTO", "ACLS",
    "AKAM", "FTNT", "PANW", "CHKP", "S", "TENB",
    "QLYS", "PCTY", "PAYC", "EPAM", "GLOB", "EXLS", "CGNX",

    # Healthcare
    "BMY", "ABBV", "AMGN", "BIIB", "REGN", "VRTX", "ALNY",
    "INCY", "EXEL", "HALO", "ACAD", "NBIX", "PRGO",
    "JAZZ", "ANIP", "LNTH",
    "HCA", "THC", "UHS", "ENSG", "ACHC",
    "MDT", "BSX", "EW", "STE", "HOLX", "IDXX",
    "ALGN", "DXCM", "PODD", "TNDM",
    "CVS", "MCK", "CAH", "ABC", "HSIC",

    # Energy
    "XOM", "CVX", "COP", "EOG", "DVN", "MRO", "APA", "FANG",
    "OVV", "SM", "MTDR", "MGY", "CTRA",
    "SLB", "HAL", "BKR", "NOV", "PTEN", "NE", "RIG",
    "PSX", "VLO", "MPC", "PBF",
    "OKE", "WMB", "KMI", "EPD", "PAA", "TRGP", "LNG",

    # Industrials
    "GE", "HON", "MMM", "EMR", "ETN", "ROK", "PH", "AME", "FAST",
    "GWW", "SWK", "SNA",
    "LMT", "RTX", "NOC", "GD", "BA", "HEI", "TDG",
    "AXON", "CACI", "LDOS", "SAIC", "BAH",
    "UPS", "FDX", "XPO", "CHRW", "ODFL", "SAIA",
    "JBHT", "KNX", "WERN",
    "URI", "BLDR", "MAS",

    # Consumer Discretionary
    "NKE", "SKX", "CROX", "DECK",
    "PVH", "RL", "TAP", "STZ", "MO", "PM",
    "YUM", "QSR", "DRI", "EAT", "TXRH", "JACK", "WEN", "MCD",
    "SBUX", "DNUT", "SHAK",
    "AN", "KMX", "LAD", "ABG", "GPI",
    "TNL", "HGV", "VAC",
    "BKNG", "EXPE", "ABNB", "UBER", "LYFT", "MTN",

    # Consumer Staples
    "KO", "PEP", "KHC", "MKC", "CAG", "SJM", "HRL",
    "TSN", "PPC",
    "SYY", "PFGC",
    "CASY", "MUSA",

    # Materials
    "NUE", "STLD", "RS", "CMC", "CLF", "MT", "AA", "KALU",
    "FCX", "SCCO", "NEM", "AEM", "WPM", "GOLD", "KGC", "PAAS",
    "ECL", "PPG", "SHW", "AXTA",
    "APD", "LIN", "CE", "LYB", "HUN", "EMN", "OLN",
    "IP", "PKG", "SON", "GEF", "SEE", "ATR", "SLGN",

    # REITs
    "SPG", "SKT", "KIM", "REG",
    "EQR", "AVB", "UDR",
    "ARE", "BXP", "SLG", "VNO",
    "PLD", "STAG", "EXR", "CUBE", "PSA",

    # Utilities
    "AEP", "SO", "DUK", "EXC", "XEL", "WEC", "AEE", "CMS", "NI",
    "OGE", "EVRG", "PNW",
    "AWK", "WTRG",

    # Communication
    "VZ", "T", "TMUS",
    "IPG", "OMC",
    "AKAM", "CIEN", "IRDM",
    "NWSA", "NYT",

    # Specialty
    "CBRE", "JLL",
    "MC", "LAZ", "EVR", "PJT", "HLI",
    "RKT", "COOP",
    "FLO", "JJSF", "FRPT",
    "ELF", "IPAR",
]))
