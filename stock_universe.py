"""
Stock universe: ~500+ US stocks, $15+, reasonable volume, beta >= 1 candidates.
Excludes mega-popular: NVDA, TSLA, MSFT, AAPL, GOOGL, META, AMZN
Focus: solid mid-large caps across all sectors with real trading activity.
Also includes high-beta small caps with strong institutional interest.
"""

# High-beta / institutionally-backed stocks (from Finviz screens)
FINVIZ_PICKS = [
    # From user's Finviz screen (institutional + volume filtered)
    "AAOI", "AEHR", "AMPX", "AXTI", "BE", "BKSY", "CC", "CNTA", "COHR",
    "COIN", "DFTX", "DOCN", "HIMS", "ICHR", "KRMN", "LASR", "NBIS",
    "NXT", "PL", "SNDK", "SRAD", "STX", "TGTX", "TNDM", "UCTT",
    "UMAC", "WDC", "WULF",
]

STOCK_UNIVERSE = FINVIZ_PICKS + [
    # Financials
    "GS", "MS", "JPM", "BAC", "WFC", "C", "AXP", "COF", "DFS", "SYF",
    "BK", "STT", "SCHW", "HOOD", "ICE", "CME", "CBOE", "NDAQ", "ALLY",
    "RF", "CFG", "HBAN", "KEY", "MTB", "USB", "PNC", "FHN", "CMA", "FITB",
    "BX", "KKR", "APO", "ARES", "CG", "BN", "TROW", "IVZ", "BEN", "AMG",
    "LNC", "MET", "PRU", "AFL", "AIG", "HIG", "TRV", "CB", "ALL", "PGR",
    "CINF", "WRB", "RE", "RNR", "AIZ", "GL", "UNM", "FNF", "FAF",

    # Technology (mid-cap, not mega)
    "IBM", "HPQ", "HPE", "DELL", "NCR", "CDW", "NTAP", "STX", "WDC",
    "AMAT", "LRCX", "KLAC", "MCHP", "SWKS", "QRVO", "MPWR", "ENPH",
    "FSLR", "SEDG", "POWI", "ON", "WOLF", "AMBA", "SLAB", "SITM",
    "CRUS", "DIOD", "IXYS", "PLAB", "ONTO", "ACLS", "FORM", "RVLV",
    "AKAM", "FTNT", "CYBR", "PANW", "CHKP", "SAIL", "S", "TENB",
    "QLYS", "VRNT", "RDWR", "RPM", "NTCT", "CSGS", "BLKB", "PCTY",
    "PAYC", "PAYO", "PRFT", "EPAM", "GLOB", "EXLS", "CGNX", "ISRG",

    # Healthcare
    "BMY", "ABBV", "AMGN", "BIIB", "REGN", "VRTX", "ALNY", "BGNE",
    "INCY", "EXEL", "HALO", "ACAD", "PTGX", "NBIX", "PRGO", "PBH",
    "JAZZ", "CERS", "ANIP", "LNTH", "NKTR", "SAGE", "AXNX", "RETA",
    "HCA", "THC", "CYH", "UHS", "ENSG", "ACHC", "AMED", "LHCG",
    "HGTY", "ADUS", "ASAN", "MODV", "OPCH", "PNTG", "NHC", "CCRN",
    "MDT", "BSX", "EW", "STE", "HOLX", "IDXX", "ABMD", "NVST",
    "XRAY", "ALGN", "DXCM", "PODD", "TNDM", "ITGR", "NVCR", "ANIK",
    "CVS", "MCK", "CAH", "ABC", "PDCO", "HSIC", "PRXL", "ORCH",

    # Energy
    "XOM", "CVX", "COP", "EOG", "PXD", "DVN", "MRO", "APA", "FANG",
    "OVV", "SM", "CRC", "MTDR", "PR", "MGY", "CTRA", "VTLE", "REX",
    "SLB", "HAL", "BKR", "NOV", "PTEN", "NE", "RIG", "VAL", "OIS",
    "PSX", "VLO", "MPC", "DK", "HFC", "PBF", "CLMT", "PARR", "DINO",
    "OKE", "WMB", "KMI", "EPD", "MMP", "PAA", "TRGP", "LNG", "GLNG",

    # Industrials
    "GE", "HON", "MMM", "EMR", "ETN", "ROK", "PH", "AME", "FAST",
    "GWW", "MSC", "AIT", "DXP", "KFRC", "MHK", "SWK", "SNA", "KMT",
    "TXT", "HII", "LMT", "RTX", "NOC", "GD", "BA", "HEI", "TDG",
    "AXON", "CACI", "LDOS", "SAIC", "BAH", "MANT", "VSE", "DRS",
    "UPS", "FDX", "XPO", "CHRW", "EXPD", "LSTR", "ODFL", "SAIA",
    "JBHT", "KNX", "WERN", "HTLD", "MRTN", "PTSI", "USX", "ARCB",
    "URI", "HEES", "RSC", "BXC", "BLDR", "MAS", "PGTI", "AWI",

    # Consumer Discretionary
    "NKE", "LULu", "UA", "SKX", "CROX", "DECK", "WWW", "HBI", "VFC",
    "PVH", "RL", "TAP", "STZ", "BF.B", "MO", "PM", "BTI", "VGR",
    "YUM", "QSR", "DRI", "EAT", "TXRH", "CAKE", "JACK", "WEN", "MCD",
    "SBUX", "DNKN", "DNUT", "FAT", "CHUY", "RRGB", "BNGO", "SHAK",
    "AN", "KMX", "LAD", "ABG", "SAH", "GPI", "PAG", "CVNA", "VRM",
    "HTZ", "CAR", "AVIS", "TNL", "HGV", "VAC", "ILG", "PLYA", "SOND",
    "BKNG", "EXPE", "TRIP", "ABNB", "UBER", "LYFT", "MTN", "VAIL",

    # Consumer Staples
    "KO", "PEP", "KHC", "MKC", "CAG", "SJM", "HRL", "LANC", "BDSX",
    "TSN", "HRL", "PPC", "SAFM", "WH", "INGR", "STKL", "UNFI", "SPTN",
    "SYY", "US", "PFGC", "CHEF", "USFD", "CORE", "VIAV", "FWRD",
    "WBA", "RAD", "CASY", "ATD", "MUSA", "NTB", "GPM", "ANDE",

    # Materials
    "NUE", "STLD", "RS", "CMC", "X", "CLF", "MT", "AA", "CENX", "KALU",
    "FCX", "SCCO", "NEM", "AEM", "WPM", "GOLD", "KGC", "EGO", "PAAS",
    "CMP", "ASH", "ECL", "PPG", "SHW", "RPM", "AXTA", "BNCC", "TREX",
    "APD", "LIN", "CE", "LYB", "HUN", "EMN", "OLN", "KRO", "TIN",
    "IP", "PKG", "SON", "GEF", "SEE", "ATR", "BERY", "SLGN",

    # Real Estate / REITs
    "SPG", "MAC", "PEI", "CBL", "SKT", "KIM", "REG", "ROIC", "WRI",
    "BRX", "AKR", "RPAI", "WHLR", "EQR", "AVB", "UDR", "AIR", "NMR",
    "ARE", "BXP", "SLG", "HIW", "CUZ", "PKY", "DEI", "VNO", "KRC",
    "COLD", "PLD", "STAG", "EXR", "CUBE", "LSI", "NSA", "PSA",

    # Utilities
    "AEP", "SO", "DUK", "EXC", "XEL", "WEC", "AEE", "CMS", "NI",
    "OGE", "EVRG", "PNW", "IDACORP", "AVA", "NWE", "MGEE",
    "AWK", "WTRG", "SJW", "MSEX", "YORW", "CTWS", "ARTNA",

    # Communication Services (non-mega)
    "VZ", "T", "TMUS", "LUMN", "CNSL", "SHEN", "USM", "TDS",
    "IPG", "OMC", "WPP", "PUBM", "TTGT", "ICLR", "MDSO", "CIEN",
    "ZAYO", "GTT", "SATS", "VSAT", "GOGO", "IRDM", "SPOK",
    "NWSA", "NWS", "MDP", "LEE", "GCI", "TPVG", "NYT", "SSP",

    # Specialty / Mixed
    "CBRE", "JLL", "HFF", "FRP", "CWK", "NEWM", "DBRG", "SFR",
    "MC", "LAZ", "EVR", "PJT", "GHL", "HLI", "MOELIS", "PWP",
    "RKT", "UWMC", "PFSI", "GHLD", "HOME", "HBFC", "COOP", "RCII",
    "AAN", "UPBD", "EZE", "PROG", "WRLD", "FCFS", "EZCORP", "DFC",
    "FLO", "JJSF", "CENT", "SMPL", "CENTA", "FRPT", "NAPA", "COTT",
    "MGPI", "WINE", "IPAR", "ELF", "COTY", "REV", "GPRE", "MGAM",
]

# Deduplicate while preserving order
seen = set()
STOCK_UNIVERSE = [x for x in STOCK_UNIVERSE if not (x in seen or seen.add(x))]
