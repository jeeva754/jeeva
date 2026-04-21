import tensorflow as tf
import random
import numpy as np
import pickle
import json
import nltk
from nltk.stem import WordNetLemmatizer
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout

# Initialize lemmatizer
lemmatizer = WordNetLemmatizer()

# Download NLTK data if not already
nltk.download('omw-1.4')
nltk.download('punkt')
nltk.download('wordnet')

# Initialize lists
words = []
classes = []
documents = []
ignore_words = ["?", "!"]

# Load intents JSON with UTF-8 encoding
with open("intent.json", encoding="utf-8") as file:
    intents = json.load(file)

# Process each pattern in the intents
for intent in intents["intents"]:
    for pattern in intent["patterns"]:
        # Tokenize each word
        tokenized_words = nltk.word_tokenize(pattern)
        words.extend(tokenized_words)
        documents.append((tokenized_words, intent["tag"]))
        if intent["tag"] not in classes:
            classes.append(intent["tag"])

# Lemmatize and lower each word, remove duplicates
words = sorted(list(set([lemmatizer.lemmatize(w.lower()) for w in words if w not in ignore_words])))
classes = sorted(list(set(classes)))

print(f"{len(documents)} documents")
print(f"{len(classes)} classes: {classes}")
print(f"{len(words)} unique lemmatized words")

# Save words and classes for later use
pickle.dump(words, open("words.pkl", "wb"))
pickle.dump(classes, open("classes.pkl", "wb"))

# Create training data
training = []
output_empty = [0] * len(classes)

for doc in documents:
    bag = []
    pattern_words = [lemmatizer.lemmatize(word.lower()) for word in doc[0]]
    for w in words:
        bag.append(1 if w in pattern_words else 0)

    # Create output row (0 for all classes, 1 for current class)
    output_row = list(output_empty)
    output_row[classes.index(doc[1])] = 1
    training.append([bag, output_row])

# Shuffle and convert to numpy array
random.shuffle(training)
training = np.array(training, dtype=object)

# Split features and labels
train_x = list(training[:, 0])
train_y = list(training[:, 1])
print("Training data created")

# Build model
model = Sequential()
model.add(Dense(128, input_shape=(len(train_x[0]),), activation="relu"))
model.add(Dropout(0.5))
model.add(Dense(64, activation="relu"))
model.add(Dropout(0.5))
model.add(Dense(len(train_y[0]), activation="softmax"))

model.summary()

# Compile model
sgd = tf.keras.optimizers.SGD(learning_rate=0.01, momentum=0.9, nesterov=True)
model.compile(loss="categorical_crossentropy", optimizer=sgd, metrics=["accuracy"])

# Train model
hist = model.fit(np.array(train_x), np.array(train_y), epochs=200, batch_size=5, verbose=1)

# Save model
model.save("chatbot_model.h5")
print("Model created and saved successfully")
