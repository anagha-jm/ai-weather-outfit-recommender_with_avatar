import pandas as pd
import joblib
import os

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score



df = pd.read_csv("data/kerala_weather.csv")

print("Dataset Loaded Successfully!")
print(df.head())

# ---------------------------------
# Create Outfit Labels
# ---------------------------------

def recommend_outfit(row):

    temp = row["max_temp"]
    rain = row["rainfall"]
    wind = row["max_speed"]

    # Heavy rain
    if rain >= 40:
        return "Rain Jacket + Waterproof Shoes + Umbrella"

    # Rain
    elif rain >= 10:
        return "Light Jacket + Umbrella"

    # Very Hot
    elif temp >= 35:
        return "T-Shirt + Shorts + Cap"

    # Hot
    elif temp >= 30:
        return "Cotton T-Shirt + Jeans"

    # Windy
    elif wind >= 25:
        return "Windproof Jacket + Jeans"

    # Pleasant
    elif temp >= 25:
        return "Hoodie + Jeans"

    else:
        return "Sweater + Jacket"

df["outfit"] = df.apply(recommend_outfit, axis=1)

# ---------------------------------
# Features
# ---------------------------------

X = df[
    [
        "rainfall",
        "min_temp",
        "max_speed",
        "max_temp",
    ]
]

# ---------------------------------
# Encode Labels
# ---------------------------------

encoder = LabelEncoder()

y = encoder.fit_transform(df["outfit"])

# ---------------------------------
# Split Dataset
# ---------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

# ---------------------------------
# Train Model
# ---------------------------------

model = RandomForestClassifier(
    n_estimators=300,
    random_state=42
)

model.fit(X_train, y_train)

# ---------------------------------
# Accuracy
# ---------------------------------

prediction = model.predict(X_test)

accuracy = accuracy_score(y_test, prediction)

print("\nModel Accuracy :", round(accuracy * 100, 2), "%")

# ---------------------------------
# Save Model
# ---------------------------------

os.makedirs("model", exist_ok=True)

joblib.dump(model, "model/outfit_model.pkl")

joblib.dump(encoder, "model/label_encoder.pkl")

print("\nModel Saved Successfully!")

print("\nAvailable Outfit Categories:")

for item in encoder.classes_:
    print("-", item)