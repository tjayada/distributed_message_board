## channel.py - a simple message channel
##

from flask import Flask, request, render_template, jsonify
import json
import requests
import math

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

# Initialize global variables
cosine_similarity_threshold = 0.25
trivia_df = pd.read_json(DATA_FILE)
vectorizer = None

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
    global trivia_df, vectorizer, cosine_similarity_threshold
    
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

    message['content'] = sentence
    messages.append({'content':message['content'], 'sender':message['sender'], 'timestamp':message['timestamp']})
    save_messages(messages)

    ###############################################################################
    # add chatbot response here
    # essentially do the same as above, but need to create answer
    ###############################################################################
    # 1. read sentence from user
        # line 89
    # 2. do some ELIZA-style transformation
        # need to write a function to do this
        # but online many examples
    # 3. translate that to emoji
        # line 90 to 94
    # 4. save the message as well
        # line 96 to 98
    
    if vectorizer is None:
        trivia_df, vectorizer = create_trivia()
    
    # Cosine similarity 
    tfidf_vector_new_message = vectorizer.transform([sentence])
    tfidf_vectors_series = csr_matrix(trivia_df['tfidf_vector'].tolist())
    cosine_similarities = cosine_similarity(tfidf_vector_new_message, tfidf_vectors_series) 
    trivia_df['cosine_similarity'] = cosine_similarities.flatten()
    df_sorted_by_cosine = trivia_df.sort_values(by='cosine_similarity', ascending=False)
    
    # Check if the top match is above the threshold
    if df_sorted_by_cosine.iloc[0]['cosine_similarity'] >= cosine_similarity_threshold:
        # most similar question
        
        # question, answer, incorrect_answers, type_of_question, similarity = df_sorted_by_cosine.iloc[0]['question', 'correct_answer', 'incorrect_answers', 'type', 'cosine_similarity']
        question, answer, incorrect_answers, type_of_question, similarity = df_sorted_by_cosine.iloc[0][['question', 'correct_answer', 'incorrect_answers', 'type', 'cosine_similarity']]
        row = df_sorted_by_cosine.iloc[0]
        question = row['question']
        answer = row['correct_answer']
        incorrect_answers = row['incorrect_answers']
        type_of_question = row['type']
        similarity = row['cosine_similarity']
        
        # add bot reply to messages...
        print("Computer sagt JA!!")
        messages.append({'content':question, 'sender':"TriviaBot", 'timestamp':time.time()})
        save_messages(messages)
    
    else:
        question, answer, incorrect_answers, type_of_question, similarity = df_sorted_by_cosine.iloc[0][['question', 'correct_answer', 'incorrect_answers', 'type', 'cosine_similarity']]
        row = df_sorted_by_cosine.iloc[0]
        question = row['question']
        answer = row['correct_answer']
        incorrect_answers = row['incorrect_answers']
        type_of_question = row['type']
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
