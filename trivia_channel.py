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

HUB_URL = 'http://localhost:5555'
HUB_AUTHKEY = '1234567890'
CHANNEL_AUTHKEY = '0987654321'
CHANNEL_NAME = "Trivia Channel"
CHANNEL_ENDPOINT = "http://localhost:5001" # don't forget to adjust in the bottom of the file
CHANNEL_FILE = 'messages.json'
DATA_FILE = 'data/triviabot/questions.json'

#HUB_URL = 'http://vm954.rz.uni-osnabrueck.de/user039/hub.wsgi'
#CHANNEL_ENDPOINT = "http://vm954.rz.uni-osnabrueck.de/user039/trivia_channel.wsgi"

# Initialize global variables
cosine_similarity_threshold = 0.25
trivia_df = pd.read_json(DATA_FILE)
vectorizer = None
send_answer = False
last_answer = None

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
        now = datetime.now()
        timestamp = now.strftime("%H:%M:%S - %d/%m/%Y")
        if sentence.lower().strip() == last_answer.lower().strip():
            messages.append({'content':"Correct!", 'sender':"TriviaBot", 'timestamp':timestamp})
        else:
            messages.append({'content':last_answer, 'sender':"TriviaBot", 'timestamp':timestamp})
        save_messages(messages)
        send_answer = False
        return "OK", 200
    # Check if the top match is above the threshold
    elif df_sorted_by_cosine.iloc[0]['cosine_similarity'] >= cosine_similarity_threshold:
        # most similar question
        
        # question, answer, incorrect_answers, type_of_question, similarity = df_sorted_by_cosine.iloc[0]['question', 'correct_answer', 'incorrect_answers', 'type', 'cosine_similarity']
        question, answer, incorrect_answers, type_of_question, similarity = df_sorted_by_cosine.iloc[0][['question', 'correct_answer', 'incorrect_answers', 'type', 'cosine_similarity']]
        row = df_sorted_by_cosine.iloc[0]
        question = html.unescape(row['question'])
        last_answer = html.unescape(row['correct_answer'])
        incorrect_answers = row['incorrect_answers']
        type_of_question = html.unescape(row['type'])
        similarity = row['cosine_similarity']
        
        now = datetime.now()
        timestamp = now.strftime("%H:%M:%S - %d/%m/%Y")
        
        # add bot reply to messages...
        print("Computer sagt JA!!")

        if type_of_question == 'multiple':
            temp_list = incorrect_answers.copy()
            temp_list.append(answer)
            random.shuffle(temp_list)
            question += " <br> "
            for idx, answer in enumerate(temp_list):
                question += f" <br> {idx+1}. {html.unescape(answer)}"
            #messages.append({'content':f"{", ".join(incorrect_answers)}", 'sender':"TriviaBot", 'timestamp':time.time()})
        elif type_of_question == 'boolean':
            question += " <br> <br> 1. True <br> 2. False"       
        messages.append({'content':question, 'sender':"TriviaBot", 'timestamp':timestamp})
        
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
