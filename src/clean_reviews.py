import pandas as pd
import os

# ----------------------------------------
# CONFIG
# ----------------------------------------

RAW_DIR = "data/raw/reviews"
PROCESSED_DIR = "data/processed"
os.makedirs(PROCESSED_DIR, exist_ok=True)

FILES = {
    "Beanlore": os.path.join(RAW_DIR, "beanlore_reviews_raw_apify.xlsx"),
    "Isobel Coffee House": os.path.join(RAW_DIR, "isobels_reviews_raw.xlsx"),
    "Third Wave Coffee": os.path.join(RAW_DIR, "thirdwave_reviews_raw.xlsx"),
}

PLACE_NAME_MAP = {
    "Beanlore - Jayanagar": "Beanlore",
    "Isobel Coffee House": "Isobel Coffee House",
    "Third Wave Coffee": "Third Wave Coffee",
}

# ----------------------------------------
# COLUMNS TO KEEP
# ----------------------------------------

KEEP_COLS = {
    "place/name":             "cafe_raw",
    "text":                   "review_text",
    "rating":                 "rating",
    "publishedAt":            "published_at",
    "visitedMonth":           "visited_month",
    "visitedYear":            "visited_year",
    "language":               "language",
    "details/atmosphere":     "atmosphere",
    "details/service":        "service",
    "details/noiseLevel":     "noise_level",
    "details/food":           "food_rating",
    "details/mealType":       "meal_type",
    "details/vegetarianOfferings/0": "vegetarian_offerings",
    "details/waitTime":       "wait_time",
    "details/pricePerPerson": "price_per_person",
    "details/parking":        "parking",
    "author/isLocalGuide":    "is_local_guide",
    "author/localGuideLevel": "local_guide_level",
    "author/reviewCount":     "author_review_count",
    "engagement/likes":       "review_likes",
    "ownerResponse/text":     "owner_response",
}

# ----------------------------------------
# LOAD AND COMBINE
# ----------------------------------------

dfs = []

for label, filepath in FILES.items():
    print(f"Loading: {label}...")
    df = pd.read_excel(filepath)
    print(f"  Rows loaded: {len(df)}")
    print(f"  Columns: {len(df.columns)}")
    dfs.append(df)

combined = pd.concat(dfs, ignore_index=True)
print(f"\nTotal rows combined: {len(combined)}")

# ----------------------------------------
# KEEP ONLY USEFUL COLUMNS
# ----------------------------------------

available = {k: v for k, v in KEEP_COLS.items() if k in combined.columns}
missing = [k for k in KEEP_COLS if k not in combined.columns]

if missing:
    print(f"\nNote: These expected columns were not found and will be skipped:")
    for m in missing:
        print(f"  - {m}")

df = combined[list(available.keys())].rename(columns=available)

# ----------------------------------------
# STANDARDIZE CAFE NAMES
# ----------------------------------------

df["cafe"] = df["cafe_raw"].map(PLACE_NAME_MAP)

unmapped = df[df["cafe"].isna()]["cafe_raw"].unique()
if len(unmapped) > 0:
    print(f"\nWarning: These cafe names were not mapped:")
    for u in unmapped:
        print(f"  - '{u}'")

df = df.drop(columns=["cafe_raw"])

cols = ["cafe"] + [c for c in df.columns if c != "cafe"]
df = df[cols]

# ----------------------------------------
# FILTER 1: DROP ROWS WITH NO REVIEW TEXT
# ----------------------------------------

before = len(df)
df = df.dropna(subset=["review_text"])
df = df[df["review_text"].str.strip() != ""]
after = len(df)
print(f"\nRows dropped (no review text): {before - after}")
print(f"Reviews remaining after text filter: {after}")

# ----------------------------------------
# FILTER 2: ENGLISH ONLY
# ----------------------------------------

before = len(df)
df = df[df["language"].isin(["en", "en-GB", "en-US"])]
after = len(df)
print(f"Non-English reviews dropped: {before - after}")
print(f"English reviews kept: {after}")

# ----------------------------------------
# CLEAN TYPES
# ----------------------------------------

# Rating: ensure numeric
df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

# Published date: parse to datetime
df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)

# Year and month: fill from published_at if missing
df["visited_year"] = pd.to_numeric(df["visited_year"], errors="coerce")
df["visited_month"] = pd.to_numeric(df["visited_month"], errors="coerce")

df["year"] = df["visited_year"].fillna(df["published_at"].dt.year)
df["month"] = df["visited_month"].fillna(df["published_at"].dt.month)

df = df.drop(
    columns=["visited_year", "visited_month"],
    errors="ignore"
)

# Local guide: boolean
df["is_local_guide"] = df["is_local_guide"].astype(str).str.upper().map(
    {"TRUE": True, "FALSE": False, "NAN": False}
)

# Owner response: boolean flag
df["has_owner_response"] = (
    df["owner_response"].notna() &
    (df["owner_response"].str.strip() != "")
)

# Likes: fill nulls with 0
df["review_likes"] = pd.to_numeric(df["review_likes"], errors="coerce").fillna(0).astype(int)

# ----------------------------------------
# FINAL SUMMARY
# ----------------------------------------

print("\n========== FINAL DATASET SUMMARY ==========")
print(f"Total reviews: {len(df)}")
print(f"\nReviews per café:")
print(df["cafe"].value_counts().to_string())
print(f"\nAverage rating per café:")
print(df.groupby("cafe")["rating"].mean().round(2).to_string())
print(f"\nLocal guide breakdown:")
print(df.groupby("cafe")["is_local_guide"].sum().to_string())
print(f"\nReviews with owner response:")
print(df.groupby("cafe")["has_owner_response"].sum().to_string())
print(f"\nDate range:")
print(f"  Earliest: {df['published_at'].min()}")
print(f"  Latest:   {df['published_at'].max()}")
print(f"\nLanguage breakdown:")
print(df["language"].value_counts().to_string())
print(f"\nColumns in final dataset:")
print(df.columns.tolist())

# ----------------------------------------
# SAVE
# ----------------------------------------

output_path = os.path.join(PROCESSED_DIR, "reviews_master.csv")
df.to_csv(output_path, index=False)
print(f"\nSaved to: {output_path}")
print(f"Final row count in saved file: {len(df)}")

with open(output_path, "r") as f:
    dff =  pd.read_csv(output_path)

if "visited_year" in dff.columns:
    print("visited_year column exists")
else:
    print("visited_year column does not exist")
    