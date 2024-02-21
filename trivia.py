from sklearn.feature_extraction.text import TfidfVectorizer

def create_trivia():
    import pandas as pd
    
    # load infos first
    questions_info = pd.read_json(f"data/triviabot/questions_info.json")
    questions_df = pd.read_json(f"data/triviabot/questions.json")
    
    
    trivia_texts = questions_df['question'] + " " + questions_df['correct_answer']  # Combine question and answer
    # TF-IDF vectors 
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_vectors = vectorizer.fit_transform(trivia_texts.tolist())
    questions_df['tfidf_vector'] = [vec.toarray()[0] for vec in tfidf_vectors]

    return questions_df, vectorizer




























'''

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


from flask_sqlalchemy import SQLAlchemy
from flask import Flask
import pandas as pd
from sqlalchemy import create_engine

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trivia.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Trivia(db.Model):
    __tablename__ = 'trivia'
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String, nullable=False)
    tfidf_vector = db.Column(db.PickleType, nullable=False)
    type = db.Column(db.String, nullable=False)
    correct_answer = db.Column(db.String, nullable=False)
    incorrect_answers = db.Column(db.PickleType, nullable=False)
    category_name = db.Column(db.String, nullable=False)
    category_id = db.Column(db.Integer, nullable=False)
    
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), nullable=False)
    channel = db.relationship('Channel', backref=db.backref('trivia', lazy=True))

    def __repr__(self):
        return f'<Trivia {self.id}: {self.question}>'

@app.before_first_request
def initialize_database():
    db.create_all()
    # Load and concatenate all questions into one DataFrame
    questions_df = pd.DataFrame()
    # Assuming you have a function to load your JSON data into DataFrame
    questions_info = pd.read_json(f"data/triviabot/questions_info.json")
    for cat_id in questions_info["category"].keys():
        questions_df = pd.concat([questions_df, pd.read_json(f"data/triviabot/questions_{cat_id}.json")])

    # Assuming you have already vectorized 'questions_df' and added 'tfidf_vector' column
    # Add rows to the database
    for _, row in questions_df.iterrows():
        trivia_entry = Trivia(
            question=row['question'],
            tfidf_vector=row['tfidf_vector'],
            type=row['type'],
            correct_answer=row['correct_answer'],
            incorrect_answers=row['incorrect_answers'],
            category_name=row['category_name'],
            category_id=row['category_id']
        )
        db.session.add(trivia_entry)
    db.session.commit()
    
    


from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix
import numpy as np

class TriviaBot:
    def __init__(self, vectorizer):
        self.vectorizer = vectorizer

    def find_relevant_question(self, message, cosine_similarity_threshold=0.35):
        # Transform the incoming message to a tfidf vector
        message_vector = self.vectorizer.transform([message])
        
        # Retrieve all tfidf vectors from the database
        questions = Trivia.query.all()
        tfidf_vectors = np.array([q.tfidf_vector for q in questions])
        
        # Calculate cosine similarities
        tfidf_vectors_matrix = csr_matrix(tfidf_vectors.tolist())
        cosine_similarities = cosine_similarity(message_vector, tfidf_vectors_matrix).flatten()
        
        # Find the most relevant question based on the threshold
        max_similarity = np.max(cosine_similarities)
        if max_similarity >= cosine_similarity_threshold:
            most_relevant_question_index = np.argmax(cosine_similarities)
            return questions[most_relevant_question_index].id
        else:
            return None
'''