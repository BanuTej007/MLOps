# Import necessary libraries
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import joblib

if __name__ == '__main__':
    # Load the Digits dataset
    digits = load_digits()
    X, y = digits.data, digits.target

    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=20)

    # Train a Random Forest classifier
    model = RandomForestClassifier(n_estimators=100, random_state=20)
    model.fit(X_train, y_train)

    # Save the model to a file
    joblib.dump(model, 'digits_model.pkl')
    
    print("The model training was successful")
