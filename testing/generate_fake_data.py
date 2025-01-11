import pandas as pd
import numpy as np


def generate_random_data():
    AMOUNT = 100
    # List of possible genders and their probabilities
    genders = ['male', 'female', 'non-binary']
    gender_probs = [0.4, 0.3, 0.3]

    # List of possible nationalities with their corresponding country names
    nationalities = {
    'USA': 0.15,
    'Canada': 0.10,
    'UK': 0.10,
    'Germany': 0.08,
    'France': 0.08,
    'Italy': 0.07,
    'Spain': 0.07,
    'Australia': 0.05,
    'India': 0.05,
    'China': 0.05,
    'Japan': 0.05,
    'Brazil': 0.04,
    'South Africa': 0.03,
    'Mexico': 0.03,
    'Russia': 0.02,
    'Argentina': 0.02,
    'Nigeria': 0.02,
    'Egypt': 0.01,
    'Saudi Arabia': 0.01,
    'South Korea': 0.01,
    }
    total_prob = sum(nationalities.values())
    nationalities = {country: prob / total_prob for country, prob in nationalities.items()}
    nationality_list = list(nationalities.keys())
    nationality_probs = list(nationalities.values())

    # List of possible study lines with their corresponding department names
    study_lines = ['Computer Science', 'Electrical Engineering', 'Human Centered AI','Mathematics and Physics', 'Biology and Chemistry', 'Mathematical Modelling']

    
    data = {
        'Name': [f"s216{i}" for i in list(range(AMOUNT))],
        "Gender": np.random.choice(genders, size=AMOUNT, p=gender_probs),
        "Nationality": np.random.choice(nationality_list, size=AMOUNT, p=nationality_probs),
        "Study line": np.random.choice(study_lines, size=AMOUNT),
    }

    df = pd.DataFrame(data)
    df.to_excel("testdata.xlsx")


if __name__ == "__main__":
    generate_random_data()