import pandas as pd
from flask import Flask, request, render_template
import logging
from datetime import datetime
from pathlib import Path

# --- Basic Setup ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- Path Setup ---
# This creates a reliable path to your project's root directory
BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"

# --- Data Loading (THE FIX) ---
# Load all necessary datasets using absolute paths
try:
    description = pd.read_csv(DATASET_DIR / "description.csv")
    precautions = pd.read_csv(DATASET_DIR / "precautions_df.csv")
    medications = pd.read_csv(DATASET_DIR / 'medications.csv')
    diets = pd.read_csv(DATASET_DIR / "diets.csv")
    workout = pd.read_csv(DATASET_DIR / "workout_df.csv")
    disease_info = pd.read_csv(DATASET_DIR / "disease_info.csv")
    symptoms_df = pd.read_csv(DATASET_DIR / "symtoms_df.csv") # Check spelling: "symtoms"

    logging.info("All datasets loaded successfully using absolute paths.")
except FileNotFoundError as e:
    # We remove exit() so we can see the full error in Netlify logs if it fails
    logging.error(f"CRITICAL ERROR: Failed to load datasets. {e}")
    # Re-raise the exception to ensure the function fails visibly in logs
    raise e

# --- Helper Functions ---

def get_current_season():
    """Determines the current season in India based on the month."""
    month = datetime.now().month
    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Summer"
    elif month in [6, 7, 8, 9]:
        return "Monsoon"
    else: # 10, 11
        return "Post-Monsoon"

def get_disease_details(dis):
    """Fetches all details for a given disease."""
    try:
        desc = " ".join(description[description['Disease'] == dis]['Description'].values)
        pre = precautions[precautions['Disease'] == dis][['Precaution_1', 'Precaution_2', 'Precaution_3', 'Precaution_4']].values.flatten().tolist()
        med = medications[medications['Disease'] == dis]['Medication'].tolist()
        die = diets[diets['Disease'] == dis]['Diet'].tolist()
        wrkout = workout[workout['disease'] == dis]['workout'].tolist()
        return desc, pre, med, die, wrkout
    except Exception as e:
        logging.error(f"Error fetching details for {dis}: {e}")
        return "No description available.", [], [], [], []

def predict_disease_with_scoring(user_symptoms, user_location):
    """
    Predicts disease by scoring based on symptoms, location, and season.
    """
    current_season = get_current_season()
    logging.info(f"User Location: {user_location}, Current Season: {current_season}")
    
    scores = {}
    
    # Iterate through each disease to calculate its score
    for disease_name in disease_info['Disease'].unique():
        related_symptoms = []
        for col in ['Symptom_1', 'Symptom_2', 'Symptom_3', 'Symptom_4']:
            s = symptoms_df[symptoms_df['Disease'] == disease_name][col].dropna().values
            if len(s) > 0:
                related_symptoms.extend(s)
        
        if not related_symptoms:
            symptom_score = 0
        else:
            match_count = sum(1 for sym in user_symptoms if sym in related_symptoms)
            symptom_score = match_count / len(related_symptoms) if len(related_symptoms) > 0 else 0

        disease_row = disease_info[disease_info['Disease'] == disease_name]
        if disease_row.empty:
            location_score, season_score = 0, 0
        else:
            disease_locations = disease_row['Location'].iloc[0]
            location_score = 1 if 'All' in disease_locations or user_location in disease_locations else 0
            
            disease_seasons = disease_row['Season'].iloc[0]
            season_score = 1 if 'All' in disease_seasons or current_season in disease_seasons else 0
        
        final_score = (0.7 * symptom_score) + (0.15 * location_score) + (0.15 * season_score)
        scores[disease_name] = round(final_score, 4)

    if not scores:
        return "Unable to predict", "Not enough data to make a prediction."

    sorted_diseases = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    predicted_disease = sorted_diseases[0][0]
    top_score = sorted_diseases[0][1]

    if top_score > 0.5:
        confidence = "High"
    elif top_score > 0.2:
        confidence = "Moderate"
    else:
        confidence = "Low"
        
    confidence_message = (f"The model predicts **{predicted_disease}** with {confidence} confidence. "
                          f"This is based on your symptoms, your location ({user_location}), "
                          f"and the current season ({current_season}).")
    
    logging.info(f"Prediction made: {predicted_disease} with score {top_score}")
    return predicted_disease, confidence_message

# --- Flask Routes ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route('/predict', methods=['POST'])
def predict():
    if request.method == 'POST':
        # FIX 1: Get location from the 'state' form field to match index.html
        location = request.form.get('state')

        # FIX 2: Get symptoms from the text input and split them into a list
        symptoms_string = request.form.get('symptoms')
        symptoms = [s.strip().lower().replace(' ', '_') for s in symptoms_string.split(',') if s.strip()] if symptoms_string else []

        # --- Validation ---
        message = ""
        if not symptoms:
            message = "Please enter at least one symptom."
        if not location:
            message = "Please select your location."
        
        if message:
            return render_template('index.html', message=message)

        # --- Prediction Logic ---
        predicted_disease, confidence_message = predict_disease_with_scoring(symptoms, location)
        
        dis_des, precautions, medications, rec_diet, workout = get_disease_details(predicted_disease)
        
        return render_template(
            'index.html',
            predicted_disease=predicted_disease,
            confidence_message=confidence_message,
            dis_des=dis_des,
            my_precautions=precautions,
            medications=medications,
            my_diet=rec_diet,
            workout=workout,
            # Pass back the user's input to show what was submitted
            submitted_symptoms=symptoms_string,
            submitted_location=location
        )
    return index()

# --- Static Page Routes ---
@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/developer')
def developer():
    return render_template("developer.html")

@app.route('/blog')
def blog():
    return render_template("blog.html")

# --- Main App Runner ---
if __name__ == '__main__':
    app.run(debug=True)