## channel.py - a simple message channel
##

from flask import Flask, request, render_template, jsonify
import json
import requests
import math
import html
from datetime import datetime
import random

# imports for chatbot's database creation
import requests
import pandas as pd
import time
from sklearn.feature_extraction.text import TfidfVectorizer

from trivia import create_trivia
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db

HUB_URL = 'https://temporary-server.de'
HUB_AUTHKEY = 'Crr-K3d-2N'
CHANNEL_AUTHKEY = '0987654321'
CHANNEL_NAME = "Trivia Channel"

#CHANNEL_ENDPOINT = "http://localhost:5001" # don't forget to adjust in the bottom of the file
CHANNEL_FILE = 'messages.json'
DATA_FILE = 'data/triviabot/questions.json'

#HUB_URL = 'http://vm954.rz.uni-osnabrueck.de/user039/hub.wsgi'
CHANNEL_ENDPOINT = "http://vm954.rz.uni-osnabrueck.de/user191/trivia_channel.wsgi"

# Initialize global variables
cosine_similarity_threshold = 0.25
trivia_df = pd.read_json(DATA_FILE)
vectorizer = None
send_answer = False
last_answer = None

def update_score(username, correct):
    # Assuming this function updates the score in scores.json
    scores_file = 'scores.json'
    try:
        with open(scores_file, 'r') as file:
            scores = json.load(file)
    except FileNotFoundError:
        scores = {}
    
    # Update or initialize the user's score
    if username in scores and correct:
        scores[username] += 1
    elif username not in scores:
        scores[username] = 1 if correct else 0
    
    # Write the updated scores back to the file
    with open(scores_file, 'w') as file:
        json.dump(scores, file)
    
    return scores.get(username, 0)

@app.route('/scores', methods=['GET'])
def show_scores():
    scores_file = 'scores.json'
    try:
        with open(scores_file, 'r') as file:
            scores = json.load(file)
        return jsonify(scores)
    except FileNotFoundError:
        return jsonify({"error": "No scores available."}), 404





@app.cli.command('register')
def register_command():
    global CHANNEL_AUTHKEY, CHANNEL_NAME, CHANNEL_ENDPOINT, DATA_FILE, trivia_df, vectorizer, cosine_similarity_threshold

    # send a POST request to server /channels
    response = requests.post(HUB_URL + '/channels', headers={'Authorization': 'authkey ' + HUB_AUTHKEY},
                             data=json.dumps({
            "name": CHANNEL_NAME,
            "endpoint": CHANNEL_ENDPOINT,
            "authkey": CHANNEL_AUTHKEY}))

    if response.status_code != 200:
        print("Error creating channel: "+str(response.status_code))
        return
    
    cosine_similarity_threshold = 0.35
    trivia_df = pd.read_json(DATA_FILE)
    trivia_df, vectorizer = create_trivia()


def check_authorization(request):
    global CHANNEL_AUTHKEY
    # check if Authorization header is present
    if 'Authorization' not in request.headers:
        return False
    # check if authorization header is valid
    if request.headers['Authorization'] != 'authkey ' + CHANNEL_AUTHKEY:
        return False
    return True

@app.route('/health', methods=['GET'])
def health_check():
    global CHANNEL_NAME
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({'name':CHANNEL_NAME}),  200

# GET: Return list of messages
@app.route('/', methods=['GET'])
def home_page():
    if not check_authorization(request):
        return "Invalid authorization", 400
    # fetch channels from server
    return jsonify(read_messages())

# POST: Send a message
@app.route('/', methods=['POST'])
def send_message():
    global trivia_df, vectorizer, cosine_similarity_threshold, send_answer, last_answer
    
    # fetch channels from server
    # check authorization header
    if not check_authorization(request):
        return "Invalid authorization", 400
    # check if message is present
    message = request.json
    if not message:
        return "No message", 400
    if not 'content' in message:
        return "No content", 400
    if not 'sender' in message:
        return "No sender", 400
    if not 'timestamp' in message:
        return "No timestamp", 400
    # add message to messages
    messages = read_messages()
    
    
    sentence = message['content']

    # Get the current date and time
    now = datetime.now()
    timestamp = now.strftime("%H:%M:%S - %d/%m/%Y")

    messages.append({'content':message['content'], 'sender':message['sender'], 'timestamp': timestamp})
    save_messages(messages)

    ###############################################################################
    # add chatbot response here
    # essentially do the same as above, but need to create answer
    ###############################################################################

    if vectorizer is None:
        trivia_df, vectorizer = create_trivia()
    
    # Cosine similarity 
    tfidf_vector_new_message = vectorizer.transform([sentence])
    tfidf_vectors_series = csr_matrix(trivia_df['tfidf_vector'].tolist())
    cosine_similarities = cosine_similarity(tfidf_vector_new_message, tfidf_vectors_series) 
    trivia_df['cosine_similarity'] = cosine_similarities.flatten()
    df_sorted_by_cosine = trivia_df.sort_values(by='cosine_similarity', ascending=False)
    
    if send_answer:
        user_answer = message['content'].strip().lower()  # Normalize user answer for comparison
        correct_answer = last_answer.strip().lower()  # Ensure we compare in the same format
        correct = user_answer == correct_answer
        user_score = update_score(message['sender'], correct)  # Update score and retrieve new score

        # Prepare the bot's response message including the score
        if correct:
            response_content = f"Correct! Good job. Your score is now {user_score}."
        else:
            response_content = f"Sorry, that's not right. The correct answer was '{last_answer}'. Your score is {user_score}."

        now = datetime.now()
        timestamp = now.strftime("%H:%M:%S - %d/%m/%Y")
        messages.append({'content': response_content, 'sender': "TriviaBot", 'timestamp': timestamp})
        save_messages(messages)

        send_answer = False  # Reset the flag as we've now responded to the answer
        return "OK", 200



    # Check if the top match is above the threshold
    elif df_sorted_by_cosine.iloc[0]['cosine_similarity'] >= cosine_similarity_threshold:
        # most similar question
        
        # question, answer, incorrect_answers, type_of_question, similarity = df_sorted_by_cosine.iloc[0]['question', 'correct_answer', 'incorrect_answers', 'type', 'cosine_similarity']
        question, answer, incorrect_answers, type_of_question, similarity = df_sorted_by_cosine.iloc[0][['question', 'correct_answer', 'incorrect_answers', 'type', 'cosine_similarity']]
        row = df_sorted_by_cosine.iloc[0]
        question = html.unescape(row['question'])
        last_answer = html.unescape(row['correct_answer'])
        incorrect_answers = html.unescape(row['incorrect_answers'])
        type_of_question = html.unescape(row['type'])
        similarity = row['cosine_similarity']
        
        now = datetime.now()
        timestamp = now.strftime("%H:%M:%S - %d/%m/%Y")
        
        # add bot reply to messages...
        print("Computer sagt JA!!")
        messages.append({'content': question, 'sender': "TriviaBot", 'timestamp': timestamp})

        if type_of_question == 'multiple':
            # Combine correct and incorrect answers, then shuffle
            all_answers = incorrect_answers + [last_answer]  # Assume incorrect_answers is a list and last_answer is a string
            random.shuffle(all_answers)  # Shuffle the answers to randomize their order

            # Format the combined answers for presentation
            formatted_answers = ', '.join(all_answers)
            
            # Add formatted answers to messages
            now = datetime.now()  # Reuse the datetime object if you want to keep the same timestamp
            timestamp = now.strftime("%H:%M:%S - %d/%m/%Y")  # Ensure consistent timestamp formatting
            messages.append({'content': formatted_answers, 'sender': "TriviaBot", 'timestamp': timestamp})

        save_messages(messages)
        send_answer = True
    
    else:
        question, answer, incorrect_answers, type_of_question, similarity = df_sorted_by_cosine.iloc[0][['question', 'correct_answer', 'incorrect_answers', 'type', 'cosine_similarity']]
        row = df_sorted_by_cosine.iloc[0]
        question = html.unescape(row['question'])
        answer = html.unescape(row['correct_answer'])
        incorrect_answers = html.unescape(row['incorrect_answers'])
        type_of_question = html.unescape(row['type'])
        similarity = row['cosine_similarity']
        
        print("Computer sagt nein!!", similarity)

    return "OK", 200

def read_messages():
    global CHANNEL_FILE
    try:
        f = open(CHANNEL_FILE, 'r')
    except FileNotFoundError:
        return []
    try:
        messages = json.load(f)
    except json.decoder.JSONDecodeError:
        messages = []
    f.close()
    return messages

def save_messages(messages):
    global CHANNEL_FILE
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(messages, f)



# Start development web server
if __name__ == '__main__':

    app.run(port=5001, debug=True)
