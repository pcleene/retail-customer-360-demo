"""Malaysian-realistic data generation helpers."""

import random
from datetime import datetime, timedelta

# --- Malaysian Name Pools ---
MALAY_FIRST_MALE = [
    "Ahmad", "Muhammad", "Mohd", "Abdul", "Ali", "Hassan", "Ibrahim", "Ismail",
    "Azman", "Faizal", "Hafiz", "Rizal", "Amir", "Zulkifli", "Kamal", "Rashid",
    "Nasir", "Razak", "Shahrul", "Fitri", "Arif", "Danial", "Syafiq", "Izzat",
    "Hakim", "Farhan", "Aziz", "Faisal", "Haris", "Imran",
]
MALAY_FIRST_FEMALE = [
    "Siti", "Nur", "Noraini", "Fatimah", "Aisyah", "Aminah", "Zainab", "Rohani",
    "Halimah", "Mariam", "Suriati", "Nadia", "Farah", "Aisha", "Yasmin", "Hana",
    "Laila", "Safiya", "Nurul", "Izzah", "Syahirah", "Nabila", "Amira", "Liyana",
    "Hanis", "Atiqah", "Balqis", "Dina", "Fatin", "Aina",
]
MALAY_LAST = [
    "bin Abdullah", "bin Ibrahim", "bin Hassan", "bin Ahmad", "bin Ismail",
    "bin Othman", "bin Yusof", "bin Mohamed", "bin Ali", "bin Razak",
    "binti Abdullah", "binti Ibrahim", "binti Hassan", "binti Ahmad", "binti Ismail",
    "binti Othman", "binti Yusof", "binti Mohamed", "binti Ali", "binti Razak",
]

CHINESE_FIRST_MALE = [
    "Wei", "Jun", "Hao", "Ming", "Jian", "Zhi", "Kai", "Chen", "Liang", "Feng",
    "Hong", "Chong", "Seng", "Keat", "Wai", "Yew", "Boon", "Kok", "Keng", "Leong",
]
CHINESE_FIRST_FEMALE = [
    "Mei", "Ling", "Xin", "Hui", "Yan", "Fang", "Li", "Jing", "Wen", "Yun",
    "Siew", "Pei", "Ai", "Cheng", "May", "Su", "Bee", "Chin", "Hooi", "Gaik",
]
CHINESE_LAST = [
    "Tan", "Lim", "Lee", "Ng", "Wong", "Chan", "Ong", "Koh", "Teh", "Goh",
    "Cheah", "Chong", "Foo", "Ho", "Khoo", "Lau", "Low", "Sim", "Yap", "Yeoh",
]

INDIAN_FIRST_MALE = [
    "Raj", "Kumar", "Ravi", "Suresh", "Ganesh", "Vijay", "Anand", "Prakash",
    "Shankar", "Ramesh", "Arjun", "Deepak", "Naveen", "Sanjay", "Arun",
    "Mohan", "Krishna", "Bala", "Thiru", "Mani",
]
INDIAN_FIRST_FEMALE = [
    "Priya", "Lakshmi", "Devi", "Shalini", "Kavitha", "Malini", "Rani", "Geetha",
    "Meena", "Nirmala", "Anitha", "Divya", "Gayathri", "Indira", "Jaya",
    "Kamala", "Latha", "Radha", "Saroja", "Uma",
]
INDIAN_LAST = [
    "a/l Krishnan", "a/l Raman", "a/l Subramaniam", "a/l Muthu", "a/l Nair",
    "a/l Pillai", "a/l Kumar", "a/l Singh", "a/l Raj", "a/l Maniam",
    "a/p Krishnan", "a/p Raman", "a/p Subramaniam", "a/p Muthu", "a/p Nair",
    "a/p Pillai", "a/p Kumar", "a/p Singh", "a/p Raj", "a/p Maniam",
]

# --- Malaysian States + Population Weight ---
STATES = {
    "Selangor": 0.22, "Kuala Lumpur": 0.12, "Johor": 0.12, "Penang": 0.07,
    "Perak": 0.08, "Sabah": 0.06, "Sarawak": 0.05, "Kedah": 0.06,
    "Kelantan": 0.05, "Pahang": 0.04, "Terengganu": 0.03, "Melaka": 0.03,
    "Negeri Sembilan": 0.03, "Perlis": 0.01, "Putrajaya": 0.02, "Labuan": 0.01,
}

# --- RetailGroup Store Locations ---
RetailGroup_STORES = [
    {"store_id": "RetailGroup-BGS", "name": "RetailGroup Bukit Tinggi", "state": "Selangor", "city": "Klang"},
    {"store_id": "RetailGroup-MOV", "name": "RetailGroup Mid Valley", "state": "Kuala Lumpur", "city": "Kuala Lumpur"},
    {"store_id": "RetailGroup-1UT", "name": "RetailGroup 1 Utama", "state": "Selangor", "city": "Petaling Jaya"},
    {"store_id": "RetailGroup-QBM", "name": "RetailGroup Queensbay Mall", "state": "Penang", "city": "Bayan Lepas"},
    {"store_id": "RetailGroup-TBR", "name": "RetailGroup Tebrau City", "state": "Johor", "city": "Johor Bahru"},
    {"store_id": "RetailGroup-IPH", "name": "RetailGroup Ipoh Station 18", "state": "Perak", "city": "Ipoh"},
    {"store_id": "RetailGroup-ALR", "name": "RetailGroup Ayer Keroh", "state": "Melaka", "city": "Melaka"},
    {"store_id": "RetailGroup-KBR", "name": "RetailGroup Kota Bharu", "state": "Kelantan", "city": "Kota Bharu"},
    {"store_id": "RetailGroup-KNT", "name": "RetailGroup Kuantan", "state": "Pahang", "city": "Kuantan"},
    {"store_id": "RetailGroup-AST", "name": "RetailGroup Alor Setar", "state": "Kedah", "city": "Alor Setar"},
    {"store_id": "RetailGroup-SHA", "name": "RetailGroup Shah Alam", "state": "Selangor", "city": "Shah Alam"},
    {"store_id": "RetailGroup-CHR", "name": "RetailGroup Cheras Selatan", "state": "Selangor", "city": "Cheras"},
    {"store_id": "RetailGroup-BDR", "name": "RetailGroup Bandar Utama", "state": "Selangor", "city": "Bandar Utama"},
    {"store_id": "RetailGroup-SRN", "name": "RetailGroup Seremban 2", "state": "Negeri Sembilan", "city": "Seremban"},
    {"store_id": "RetailGroup-MKN", "name": "RetailGroup Mahkota Cheras", "state": "Selangor", "city": "Cheras"},
    {"store_id": "RetailGroup-WNG", "name": "RetailGroup Wangsa Maju", "state": "Kuala Lumpur", "city": "Kuala Lumpur"},
    {"store_id": "RetailGroup-SKD", "name": "RetailGroup Seri Kembangan", "state": "Selangor", "city": "Seri Kembangan"},
    {"store_id": "RetailGroup-BMC", "name": "RetailGroup Bukit Mertajam", "state": "Penang", "city": "Bukit Mertajam"},
    {"store_id": "RetailGroup-KUC", "name": "RetailGroup Kuching Central", "state": "Sarawak", "city": "Kuching"},
    {"store_id": "RetailGroup-KKN", "name": "RetailGroup Kota Kinabalu", "state": "Sabah", "city": "Kota Kinabalu"},
    {"store_id": "RetailGroup-BTW", "name": "RetailGroup Batu Pahat", "state": "Johor", "city": "Batu Pahat"},
    {"store_id": "RetailGroup-KLG", "name": "RetailGroup Kulai", "state": "Johor", "city": "Kulai"},
    {"store_id": "RetailGroup-TGN", "name": "RetailGroup Tg. Malim", "state": "Perak", "city": "Tanjung Malim"},
    {"store_id": "RetailGroup-SBJ", "name": "RetailGroup Subang Jaya", "state": "Selangor", "city": "Subang Jaya"},
    {"store_id": "RetailGroup-PJY", "name": "RetailGroup Putrajaya", "state": "Putrajaya", "city": "Putrajaya"},
    {"store_id": "RetailGroup-BKL", "name": "RetailGroup Bukit Indah", "state": "Johor", "city": "Johor Bahru"},
    {"store_id": "RetailGroup-SGR", "name": "RetailGroup Sungai Petani", "state": "Kedah", "city": "Sungai Petani"},
    {"store_id": "RetailGroup-KRK", "name": "RetailGroup Kuala Terengganu", "state": "Terengganu", "city": "Kuala Terengganu"},
    {"store_id": "RetailGroup-TPN", "name": "RetailGroup Taiping", "state": "Perak", "city": "Taiping"},
    {"store_id": "RetailGroup-CNY", "name": "RetailGroup Rawang", "state": "Selangor", "city": "Rawang"},
    # MaxValu / RetailGroup BiG
    {"store_id": "MXV-MV1", "name": "MaxValu Mid Valley", "state": "Kuala Lumpur", "city": "Kuala Lumpur"},
    {"store_id": "MXV-PJ1", "name": "MaxValu PJ Seksyen 17", "state": "Selangor", "city": "Petaling Jaya"},
    {"store_id": "MXV-AMP", "name": "MaxValu Ampang", "state": "Selangor", "city": "Ampang"},
    {"store_id": "BIG-KPG", "name": "RetailGroup BiG Kepong", "state": "Kuala Lumpur", "city": "Kuala Lumpur"},
    {"store_id": "BIG-MKR", "name": "RetailGroup BiG Mid Valley", "state": "Kuala Lumpur", "city": "Kuala Lumpur"},
    {"store_id": "BIG-WNG", "name": "RetailGroup BiG Wangsa Maju", "state": "Kuala Lumpur", "city": "Kuala Lumpur"},
    {"store_id": "BIG-SBG", "name": "RetailGroup BiG Subang", "state": "Selangor", "city": "Subang Jaya"},
    {"store_id": "BIG-SHA", "name": "RetailGroup BiG Shah Alam", "state": "Selangor", "city": "Shah Alam"},
    {"store_id": "BIG-JBR", "name": "RetailGroup BiG Johor Bahru", "state": "Johor", "city": "Johor Bahru"},
    {"store_id": "BIG-PNG", "name": "RetailGroup BiG Penang", "state": "Penang", "city": "George Town"},
    # RetailGroup Credit branches
    {"store_id": "ACR-KL1", "name": "RetailGroup Credit KL", "state": "Kuala Lumpur", "city": "Kuala Lumpur"},
    {"store_id": "ACR-PJ1", "name": "RetailGroup Credit PJ", "state": "Selangor", "city": "Petaling Jaya"},
    {"store_id": "ACR-JB1", "name": "RetailGroup Credit JB", "state": "Johor", "city": "Johor Bahru"},
    {"store_id": "ACR-PNG", "name": "RetailGroup Credit Penang", "state": "Penang", "city": "George Town"},
    {"store_id": "ACR-IPH", "name": "RetailGroup Credit Ipoh", "state": "Perak", "city": "Ipoh"},
    # RetailGroup Bank digital (no physical)
    {"store_id": "ABK-DIG", "name": "RetailGroup Bank Digital", "state": "Kuala Lumpur", "city": "Kuala Lumpur"},
    {"store_id": "ABK-APP", "name": "RetailGroup Bank App", "state": "Kuala Lumpur", "city": "Kuala Lumpur"},
    {"store_id": "ABK-WEB", "name": "RetailGroup Bank Web", "state": "Kuala Lumpur", "city": "Kuala Lumpur"},
    {"store_id": "ABK-KIO", "name": "RetailGroup Bank Kiosk", "state": "Selangor", "city": "Petaling Jaya"},
    {"store_id": "ABK-PRT", "name": "RetailGroup Bank Partner", "state": "Selangor", "city": "Shah Alam"},
]

ENTITIES = ["RetailGroup Credit", "RetailGroup Co", "RetailGroup Bank"]
SEGMENTS = ["retail_only", "credit_only", "bank_only", "retail_credit", "retail_bank", "credit_bank", "tri_entity"]
TIERS = ["Basic", "Silver", "Gold", "Platinum"]
TIER_WEIGHTS = [0.60, 0.25, 0.12, 0.03]
CHANNELS = ["in_store", "mobile_app", "website", "email", "sms", "call_center"]

PRODUCT_CATEGORIES = {
    "grocery": ["Rice", "Cooking Oil", "Instant Noodles", "Milk", "Eggs", "Bread", "Vegetables", "Fruits",
                 "Frozen Food", "Snacks", "Beverages", "Condiments", "Canned Food", "Cereal", "Noodles"],
    "electronics": ["Smartphone", "Laptop", "Tablet", "Headphones", "Smartwatch", "Camera", "TV",
                     "Air Purifier", "Robot Vacuum", "Bluetooth Speaker", "Power Bank", "Earbuds"],
    "fashion": ["T-Shirt", "Jeans", "Dress", "Shoes", "Handbag", "Watch", "Sunglasses",
                "Sneakers", "Jacket", "Polo Shirt", "Skirt", "Scarf"],
    "household": ["Detergent", "Toilet Paper", "Air Freshener", "Cleaning Supplies", "Kitchen Towel",
                   "Broom", "Mop", "Storage Container", "Bed Sheet", "Pillow", "Curtain", "Towel"],
    "health_beauty": ["Skincare", "Shampoo", "Toothpaste", "Supplement", "Face Mask", "Perfume",
                       "Body Lotion", "Lip Balm", "Sunscreen", "Hair Oil", "Makeup Kit", "Serum"],
}

SUPPLIERS = [
    "SUP-NESTLE-MY", "SUP-UNILEVER-MY", "SUP-PG-MY", "SUP-SAMSUNG-MY", "SUP-APPLE-MY",
    "SUP-HONDA-MY", "SUP-PANASONIC-MY", "SUP-LG-MY", "SUP-COLGATE-MY", "SUP-LOREAL-MY",
    "SUP-DUTCH-MY", "SUP-MAGGI-MY", "SUP-GARDENIA-MY", "SUP-MAMEE-MY", "SUP-YEOS-MY",
    "SUP-BRAND-TOPS", "SUP-BRAND-CARE", "SUP-BRAND-HOME", "SUP-BRAND-ELEC", "SUP-BRAND-FASH",
]

CAMPAIGN_TYPES = ["cross_sell", "upsell", "retention", "reactivation", "loyalty_upgrade"]

# --- GeoJSON Coordinates for Malaysian Stores [longitude, latitude] ---
STORE_COORDINATES = {
    "RetailGroup-BGS": [101.7429, 3.0319],   # Klang
    "RetailGroup-MOV": [101.6773, 3.1178],   # Mid Valley KL
    "RetailGroup-1UT": [101.6153, 3.1506],   # 1 Utama PJ
    "RetailGroup-QBM": [100.3081, 5.3328],   # Queensbay Penang
    "RetailGroup-TBR": [103.7414, 1.5419],   # Tebrau JB
    "RetailGroup-IPH": [101.0829, 4.5975],   # Ipoh
    "RetailGroup-ALR": [102.2915, 2.2621],   # Ayer Keroh Melaka
    "RetailGroup-KBR": [102.2386, 6.1254],   # Kota Bharu
    "RetailGroup-KNT": [103.4179, 3.8077],   # Kuantan
    "RetailGroup-AST": [100.3977, 6.1184],   # Alor Setar
    "RetailGroup-SHA": [101.5322, 3.0733],   # Shah Alam
    "RetailGroup-CHR": [101.7642, 3.0524],   # Cheras
    "RetailGroup-BDR": [101.6115, 3.1516],   # Bandar Utama
    "RetailGroup-SRN": [101.9367, 2.7297],   # Seremban
    "RetailGroup-MKN": [101.7656, 3.0400],   # Mahkota Cheras
    "RetailGroup-WNG": [101.7339, 3.2002],   # Wangsa Maju
    "RetailGroup-SKD": [101.7122, 3.0280],   # Seri Kembangan
    "RetailGroup-BMC": [100.4543, 5.3636],   # Bukit Mertajam
    "RetailGroup-KUC": [110.3593, 1.5533],   # Kuching
    "RetailGroup-KKN": [116.0735, 5.9804],   # Kota Kinabalu
    "RetailGroup-BTW": [102.9316, 1.8548],   # Batu Pahat
    "RetailGroup-KLG": [103.6029, 1.6602],   # Kulai
    "RetailGroup-TGN": [101.5261, 3.6858],   # Tanjung Malim
    "RetailGroup-SBJ": [101.5879, 3.0570],   # Subang Jaya
    "RetailGroup-PJY": [101.6964, 2.9264],   # Putrajaya
    "RetailGroup-BKL": [103.6338, 1.5773],   # Bukit Indah JB
    "RetailGroup-SGR": [100.4874, 5.6468],   # Sungai Petani
    "RetailGroup-KRK": [103.1324, 5.3117],   # Kuala Terengganu
    "RetailGroup-TPN": [100.7398, 4.8553],   # Taiping
    "RetailGroup-CNY": [101.5761, 3.3213],   # Rawang
    # MaxValu / RetailGroup BiG
    "MXV-MV1": [101.6773, 3.1178],
    "MXV-PJ1": [101.6346, 3.1068],
    "MXV-AMP": [101.7600, 3.1500],
    "BIG-KPG": [101.6340, 3.2108],
    "BIG-MKR": [101.6773, 3.1178],
    "BIG-WNG": [101.7339, 3.2002],
    "BIG-SBG": [101.5879, 3.0570],
    "BIG-SHA": [101.5322, 3.0733],
    "BIG-JBR": [103.7414, 1.5419],
    "BIG-PNG": [100.3288, 5.4141],
    # RetailGroup Credit branches
    "ACR-KL1": [101.6958, 3.1390],
    "ACR-PJ1": [101.6346, 3.1068],
    "ACR-JB1": [103.7414, 1.5419],
    "ACR-PNG": [100.3288, 5.4141],
    "ACR-IPH": [101.0829, 4.5975],
    # RetailGroup Bank digital
    "ABK-DIG": [101.6958, 3.1390],
    "ABK-APP": [101.6958, 3.1390],
    "ABK-WEB": [101.6958, 3.1390],
    "ABK-KIO": [101.6346, 3.1068],
    "ABK-PRT": [101.5322, 3.0733],
}

# --- RetailGroup Credit Product Templates ---
CREDIT_PRODUCT_TEMPLATES = [
    {"product_type": "credit_card", "product_name": "RetailGroup Credit Card Classic", "product_code": "ACC-CLASSIC", "limit_range": (3000, 10000), "interest_rate_range": (12.0, 18.0), "tenure_months": None},
    {"product_type": "credit_card", "product_name": "RetailGroup Credit Card Gold", "product_code": "ACC-GOLD", "limit_range": (10000, 30000), "interest_rate_range": (10.0, 15.0), "tenure_months": None},
    {"product_type": "credit_card", "product_name": "RetailGroup Visa Signature", "product_code": "ACC-VSIG", "limit_range": (30000, 100000), "interest_rate_range": (8.0, 15.0), "tenure_months": None},
    {"product_type": "personal_loan", "product_name": "RetailGroup Personal Financing-i", "product_code": "APF-I", "limit_range": (5000, 50000), "interest_rate_range": (4.5, 9.0), "tenure_months": (12, 60)},
    {"product_type": "auto_finance", "product_name": "RetailGroup Auto Easy", "product_code": "AAE-STD", "limit_range": (20000, 150000), "interest_rate_range": (3.5, 6.0), "tenure_months": (12, 84)},
    {"product_type": "motorcycle_finance", "product_name": "RetailGroup Moto Plan", "product_code": "AMP-STD", "limit_range": (3000, 15000), "interest_rate_range": (5.0, 10.0), "tenure_months": (12, 60)},
]

PRODUCT_ATTRIBUTES = {
    "grocery": {
        "is_halal_certified": [True, True, True, False],  # 75% halal
        "is_organic": [False, False, False, False, True],  # 20% organic
        "weight_g": [100, 200, 250, 360, 500, 750, 1000, 1500, 2000],
        "country_of_origin": ["Malaysia", "Malaysia", "Malaysia", "Thailand", "Indonesia", "China", "Japan", "Australia"],
        "shelf_life_days": [7, 14, 30, 90, 180, 365, 730],
    },
    "electronics": {
        "warranty_months": [6, 12, 12, 24, 24, 36],
        "color_options": [["Black", "Silver"], ["Black", "White", "Blue"], ["Phantom Black", "Cream", "Lavender"], ["Space Gray", "Silver", "Gold"]],
        "storage_gb": [32, 64, 128, 128, 256, 256, 512, 1024],
        "model_year": [2024, 2025, 2025, 2026, 2026, 2026],
        "energy_rating": ["3-star", "4-star", "4-star", "5-star", "5-star"],
    },
    "fashion": {
        "sizes": [["S", "M", "L", "XL"], ["XS", "S", "M", "L", "XL", "XXL"], ["Free Size"]],
        "color_options": [["Black", "White", "Navy"], ["Red", "Blue", "Green", "Black"], ["Beige", "Brown", "Olive"]],
        "material": ["cotton", "polyester", "cotton blend", "denim", "silk", "linen", "nylon"],
        "season": ["all-year", "all-year", "all-year", "summer", "monsoon"],
    },
    "household": {
        "pack_size": ["500ml", "1L", "2L", "3L", "5L", "100g", "250g", "500g", "1kg"],
        "scent": ["lemon", "lavender", "ocean", "pine", "unscented", "floral", "citrus"],
        "is_eco_friendly": [False, False, False, True, True],
    },
    "health_beauty": {
        "skin_type": ["all", "all", "oily", "dry", "sensitive", "combination"],
        "is_dermatologist_tested": [True, True, True, False],
        "spf": [0, 0, 15, 30, 30, 50, 50],
        "volume_ml": [30, 50, 75, 100, 150, 200, 250, 400, 500],
    },
}

PRODUCT_TAGS = {
    "grocery": {"halal": 0.7, "organic": 0.15, "imported": 0.3, "bestseller": 0.1, "local_brand": 0.5, "new_arrival": 0.08, "RetailGroup_exclusive": 0.05},
    "electronics": {"bestseller": 0.08, "imported": 0.7, "new_arrival": 0.15, "limited_edition": 0.05, "RetailGroup_exclusive": 0.1},
    "fashion": {"bestseller": 0.1, "imported": 0.4, "new_arrival": 0.2, "limited_edition": 0.08, "clearance": 0.1, "local_brand": 0.3},
    "household": {"halal": 0.2, "organic": 0.1, "imported": 0.35, "bestseller": 0.08, "local_brand": 0.4, "RetailGroup_exclusive": 0.1},
    "health_beauty": {"bestseller": 0.12, "imported": 0.5, "new_arrival": 0.15, "limited_edition": 0.05, "RetailGroup_exclusive": 0.08, "organic": 0.1},
}

SUPPORT_NOTES = {
    "billing": [
        "Customer disputed RM{amount:.2f} charge, refunded after verification.",
        "Clarified auto-debit schedule for credit card payment.",
        "Adjusted billing cycle as requested — next statement date moved to 15th.",
        "Member queried double charge — confirmed duplicate, reversed within 24h.",
    ],
    "product": [
        "Customer enquired about warranty claim for electronics purchase.",
        "Provided product exchange for defective item — replacement shipped.",
        "Guided customer on using RetailGroup mobile app for product tracking.",
        "Escalated product safety concern to quality assurance team.",
    ],
    "delivery": [
        "Online grocery order delayed {days} days — issued RM{voucher} voucher as goodwill.",
        "Rescheduled delivery to customer's preferred time slot.",
        "Confirmed click-and-collect order ready at {store} store.",
        "Investigated missing item from delivery — replacement dispatched.",
    ],
    "account": [
        "Updated customer contact details — new phone number verified.",
        "Assisted with RetailGroup Bank app password reset.",
        "Processed tier upgrade request — Gold status effective immediately.",
        "Linked RetailGroup Credit card to RetailGroup Co loyalty account.",
    ],
    "loyalty": [
        "Member queried point expiry — explained 12-month rule, sent FAQ link.",
        "Transferred {points} points between family accounts as requested.",
        "Resolved birthday month bonus points that were not credited.",
        "Explained tier qualification criteria — customer {gap} points from next tier.",
    ],
    "complaint": [
        "Customer dissatisfied with in-store service — escalated to store manager.",
        "Resolved pricing discrepancy between shelf and checkout — refunded difference.",
        "Addressed long queue complaint — suggested self-checkout and mobile app.",
        "Forwarded cleanliness feedback to facilities management at {store}.",
    ],
}

SUPPORT_SUBCATEGORIES = {
    "billing": ["charge_dispute", "payment_query", "billing_cycle", "refund_request", "auto_debit"],
    "product": ["warranty_claim", "product_exchange", "product_enquiry", "safety_concern", "availability"],
    "delivery": ["delivery_delay", "missing_item", "reschedule", "click_and_collect", "wrong_item"],
    "account": ["profile_update", "password_reset", "tier_change", "account_linking", "card_replacement"],
    "loyalty": ["points_expiry", "points_transfer", "bonus_points", "tier_query", "redemption_issue"],
    "complaint": ["service_quality", "pricing_error", "queue_wait", "cleanliness", "staff_behavior"],
}

ANCHOR_TENANTS = [
    "Uniqlo", "Daiso", "MR.DIY", "TGV Cinemas", "GSC", "Padini", "Nando's",
    "KFC", "Starbucks", "Old Town White Coffee", "Sushi King", "Pizza Hut",
    "Guardian", "Watsons", "Popular Bookstore", "Miniso", "Cotton On",
    "H&M", "Brands Outlet", "Sports Direct", "Harvey Norman",
]

STORE_SERVICES = ["delivery", "click_and_collect", "installation", "gift_wrapping", "alterations", "key_cutting", "photo_printing"]

LIFECYCLE_STAGES = ["new", "growing", "mature", "declining", "clearance"]
LIFECYCLE_WEIGHTS = [0.10, 0.20, 0.50, 0.15, 0.05]


def random_state() -> str:
    states = list(STATES.keys())
    weights = list(STATES.values())
    return random.choices(states, weights=weights, k=1)[0]


def random_malaysian_name(ethnicity: str | None = None) -> tuple[str, str]:
    """Return (full_name, ethnicity)."""
    if ethnicity is None:
        ethnicity = random.choices(["malay", "chinese", "indian"], weights=[0.60, 0.25, 0.15], k=1)[0]

    gender = random.choice(["male", "female"])
    if ethnicity == "malay":
        first = random.choice(MALAY_FIRST_MALE if gender == "male" else MALAY_FIRST_FEMALE)
        last = random.choice([l for l in MALAY_LAST if l.startswith("bin ") == (gender == "male")])
        return f"{first} {last}", ethnicity
    elif ethnicity == "chinese":
        first = random.choice(CHINESE_FIRST_MALE if gender == "male" else CHINESE_FIRST_FEMALE)
        last = random.choice(CHINESE_LAST)
        return f"{last} {first}", ethnicity
    else:
        first = random.choice(INDIAN_FIRST_MALE if gender == "male" else INDIAN_FIRST_FEMALE)
        last = random.choice([l for l in INDIAN_LAST if l.startswith("a/l ") == (gender == "male")])
        return f"{first} {last}", ethnicity


def random_ic_number(birth_year: int | None = None) -> str:
    """Generate Malaysian IC number format: YYMMDD-SS-NNNN."""
    if birth_year is None:
        birth_year = random.randint(1960, 2000)
    yy = f"{birth_year % 100:02d}"
    mm = f"{random.randint(1, 12):02d}"
    dd = f"{random.randint(1, 28):02d}"
    state_code = f"{random.randint(1, 16):02d}"
    seq = f"{random.randint(1, 9999):04d}"
    return f"{yy}{mm}{dd}-{state_code}-{seq}"


def random_date_range(start: datetime, end: datetime) -> datetime:
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)


def stores_in_state(state: str) -> list[dict]:
    return [s for s in RetailGroup_STORES if s["state"] == state]


def random_store(state: str | None = None) -> dict:
    if state:
        candidates = stores_in_state(state)
        if candidates:
            return random.choice(candidates)
    return random.choice(RetailGroup_STORES)


def random_channel_engagement_rates() -> dict[str, dict]:
    """Generate per-channel engagement rates."""
    rates = {}
    for ch in ["email", "sms", "push_notification", "in_app", "whatsapp"]:
        base = random.uniform(0.05, 0.40)
        rates[ch] = {
            "open_rate": round(base + random.uniform(0, 0.15), 3),
            "ctr": round(base * random.uniform(0.2, 0.5), 3),
            "conversion_rate": round(base * random.uniform(0.05, 0.20), 3),
        }
    return rates


def store_geojson(store_id: str) -> dict | None:
    coords = STORE_COORDINATES.get(store_id)
    if coords:
        return {"type": "Point", "coordinates": coords}
    return None


def random_product_attributes(category: str) -> dict:
    """Generate random product attributes based on category."""
    pool = PRODUCT_ATTRIBUTES.get(category, {})
    attrs = {}
    for key, values in pool.items():
        attrs[key] = random.choice(values)
    return attrs


def random_product_tags(category: str) -> list[str]:
    """Generate random product tags based on category with realistic frequency."""
    tag_probs = PRODUCT_TAGS.get(category, {})
    return [tag for tag, prob in tag_probs.items() if random.random() < prob]


def random_support_note(category: str, **kwargs) -> str:
    """Generate a random support note for a given category."""
    templates = SUPPORT_NOTES.get(category, ["Resolved customer inquiry."])
    note = random.choice(templates)
    defaults = {"amount": round(random.uniform(10, 500), 2), "days": random.randint(1, 5),
                "voucher": random.choice([10, 20, 30, 50]), "store": random.choice(RetailGroup_STORES)["name"],
                "points": random.randint(100, 5000), "gap": random.randint(100, 2000)}
    defaults.update(kwargs)
    try:
        return note.format(**defaults)
    except (KeyError, IndexError):
        return note
