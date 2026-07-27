import pandas as pd
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report

print("1. Loading the Breast Cancer dataset...")
data = load_breast_cancer()

# Convert to a Pandas DataFrame so it looks like an Excel spreadsheet
df = pd.DataFrame(data.data, columns=data.feature_names)
# Add the 'Target' column (0 = Benign/Harmless, 1 = Malignant/Cancerous)
df['Target'] = data.target

print(f"Loaded {df.shape[0]} patients and {df.shape[1]-1} tumor features.")
print("Here are the first 3 rows of our data:")
print(df.head(3))
print("-" * 50)

# 2. Split the Data
print("2. Splitting the data into Training and Testing sets...")
X = df.drop('Target', axis=1) # X is the tumor features (the questions)
y = df['Target']              # y is the diagnosis (the answers we want to predict)

# We use 80% of data to train the model, and hide 20% to test it later
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"Training on {X_train.shape[0]} patients, Testing on {X_test.shape[0]} patients.")
print("-" * 50)

# 3. Choose the Model
print("3. Choosing the Decision Tree model...")
model = DecisionTreeClassifier(random_state=42)

# 4. Train the Model
print("4. Training the model (learning the patterns)...")
model.fit(X_train, y_train)
print("Training complete!")
print("-" * 50)

# 5. Test the Model
print("5. Testing the model on unseen patients...")
predictions = model.predict(X_test)

# Calculate accuracy
accuracy = accuracy_score(y_test, predictions)
print(f"Success! The model's accuracy on unseen data is: {accuracy * 100:.2f}%\n")

print("Detailed Medical Report:")
print(classification_report(y_test, predictions, target_names=['Malignant (Cancerous)', 'Benign (Harmless)']))
