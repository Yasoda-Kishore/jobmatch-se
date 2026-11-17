import pandas as pd

ads = pd.read_json("data/raw/ads.jsonl", lines=True)

print("Number of ads:", len(ads))
print("\nTop 10 cities:")
print(ads["city"].value_counts().head(10))

# Simple guess: Swedish text contains words like "och", "att", "vi"
swedish_words = [" och ", " att ", " vi ", " för ", " med "]
ads["is_swedish"] = ads["text"].apply(lambda t: sum(w in t.lower() for w in swedish_words) >= 3)
print("\nSwedish ads:", ads["is_swedish"].sum(), " English ads:", (~ads["is_swedish"]).sum())

ads["length"] = ads["text"].str.len()
print("\nAverage text length (characters):", int(ads["length"].mean()))