import os
import requests
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_pymongo import PyMongo
from flask_cors import CORS 
from apscheduler.schedulers.background import BackgroundScheduler
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash 

app = Flask(__name__)

# Initialize SocketIO
socket = SocketIO(app)

# MongoDB Atlas URI (replace with your credentials)
app.config["MONGO_URI"] = "mongodb+srv://cyrenaburke:ygxYNsTwdrbTAXGC@cluster0.sgudd.mongodb.net/news_feed?tls=true&tlsAllowInvalidCertificates=true"
app.config["SECRET_KEY"] = "your-secret-key"

# Initialize MongoDB client
mongo = PyMongo(app)
CORS(app)

# NewsAPI Key
NEWS_API_KEY = 'f3a094f995904af195df8a9c9e45406e'
NEWS_API_URL = 'https://newsapi.org/v2/everything'

# Load BERT Model and Tokenizer
MODEL_NAME = 'bert-base-uncased'
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)

def get_embedding(text):
    """Get BERT embedding for a given text."""
    inputs = tokenizer(text, return_tensors='pt', truncation=True, max_length=512, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state[:, 0, :].squeeze().numpy()

def calculate_similarity(embedding1, embedding2):
    """Calculate cosine similarity between two embeddings."""
    return torch.nn.functional.cosine_similarity(
        torch.tensor(embedding1), torch.tensor(embedding2), dim=0
    ).item()

# Beginning of Routes
@app.route('/')
def landing():
    return render_template('landing.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = mongo.db.users.find_one({'username': username})

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/home')
def home():
    if 'username' in session:
        username = session['username']
        news = fetch_news()
        recommendations = recommend_articles(username)

        # Add like status and like count to news and recommendations
        for article in news:
            article['liked'] = username in article.get('liked_by', [])
            article['likes'] = len(article.get('liked_by', []))

        for rec_article in recommendations:
            rec_article['liked'] = username in rec_article.get('liked_by', [])
            rec_article['likes'] = len(rec_article.get('liked_by', []))

        return render_template('home.html', username=username, news=news, recommendations=recommendations)
    else:
        return redirect(url_for('login'))

@app.route('/summarize/<article_id>', methods=['GET'])
def summarize_article(article_id):
    """Summarize an article."""
    article = mongo.db.articles.find_one({'_id': ObjectId(article_id)})
    if not article:
        return jsonify({'error': 'Article not found'}), 404

    content = article.get('content', '')
    embedding = get_embedding(content)

    mongo.db.articles.update_one(
        {'_id': ObjectId(article_id)},
        {'$set': {'bert_embedding': embedding.tolist()}}
    )

    return jsonify({'summary': content[:150] + '...', 'embedding': embedding.tolist()})

@app.route('/search', methods=['POST'])
def search_articles():
    """Search for articles using semantic similarity."""
    query = request.json.get('query', '')
    if not query:
        return jsonify({'error': 'Query is required'}), 400

    query_embedding = get_embedding(query)

    articles = list(mongo.db.articles.find())
    for article in articles:
        article_embedding = article.get('bert_embedding')
        if article_embedding:
            article['similarity'] = calculate_similarity(query_embedding, article_embedding)

    articles.sort(key=lambda x: x.get('similarity', 0), reverse=True)
    return jsonify({'results': articles[:10]})


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('landing'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        existing_user = mongo.db.users.find_one({'username': username})
        if existing_user:
            flash('Username already exists, choose another one', 'danger')
            return redirect(url_for('register'))

        mongo.db.users.insert_one({
            'username': username,
            'password': hashed_password
        })
        flash('Registration successful, please log in', 'success')

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/track_time', methods=['POST'])
def track_time():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 403

    username = session['username']
    user = mongo.db.users.find_one({'username': username})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.json
    article_url = data.get('url')
    increment_time = data.get('time_spent', 0)

    if not article_url or increment_time <= 0:
        return jsonify({'error': 'Invalid input'}), 400

    # Increment the user's time spent on this article, keyed by their username
    mongo.db.articles.update_one(
        {'url': article_url},
        {'$inc': {f'time_spent.{username}': increment_time}}
    )

    return jsonify({'success': True, 'time_spent_increment': increment_time})


@app.route('/like', methods=['POST'])
def like_article():
    """Like or unlike an article."""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 403

    username = session['username']
    article_url = request.json.get('url')
    if not article_url:
        return jsonify({'error': 'Invalid article URL'}), 400

    article = mongo.db.articles.find_one({'url': article_url}, {'_id': 1, 'liked_by': 1})
    if not article:
        return jsonify({'error': 'Article not found'}), 404

    article_id = article['_id']
    liked = username in article.get('liked_by', [])

    if liked:
        # Unlike the article
        mongo.db.articles.update_one(
            {'_id': article_id},
            {'$pull': {'liked_by': username}}
        )
        new_liked_status = False
    else:
        # Like the article
        mongo.db.articles.update_one(
            {'_id': article_id},
            {'$addToSet': {'liked_by': username}}
        )
        new_liked_status = True

    # Recalculate like count
    updated_article = mongo.db.articles.find_one({'_id': article_id}, {'liked_by': 1})
    like_count = len(updated_article.get('liked_by', []))

    # Update the like count in the database
    mongo.db.articles.update_one(
        {'_id': article_id},
        {'$set': {'likes': like_count}}
    )

    return jsonify({'liked': new_liked_status, 'likes': like_count})

@app.route('/store_context', methods=['POST'])
def store_context():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 403

    username = session['username']
    user = mongo.db.users.find_one({'username': username})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user_id = user['_id']
    data = request.json.get('contextual_data', {})

    # data may contain 'location' and 'time_of_access' now
    # Example structure:
    # {
    #   "theme": "dark",
    #   "viewport": {"width": 1920, "height": 1080},
    #   "reading_mode": "focus",
    #   "location": { "latitude": <lat>, "longitude": <lng> },
    #   "time_of_access": "2024-12-06T12:34:56.789Z"
    # }

    mongo.db.contextual_data.update_one(
        {'user_id': user_id},
        {'$set': {'context': data}},
        upsert=True
    )

    return jsonify({'success': True})


# Function to fetch news from NewsAPI and store in MongoDB if not already stored
def fetch_news():
    """Fetch news articles and store them in MongoDB."""
    params = {
        'apiKey': NEWS_API_KEY,
        'q': 'news',
        'pageSize': 20,
        'sortBy': 'publishedAt',
        'language': 'en',
        'domains': 'bbc.co.uk,cnn.com,wired.com,nytimes.com'
    }

    response = requests.get(NEWS_API_URL, params=params)
    if response.status_code != 200:
        print(f"Error fetching news: {response.status_code}")
        return []

    articles = response.json().get('articles', [])
    for article in articles:
        category = categorize_article(article)
        mongo.db.articles.update_one(
            {'url': article['url']},
            {
                '$set': {
                    'title': article.get('title'),
                    'description': article.get('description'),
                    'urlToImage': article.get('urlToImage'),
                    'publishedAt': article.get('publishedAt'),
                    'content': article.get('content'),
                    'category': category,
                },
                '$setOnInsert': {
                    'bert_embedding': None,
                    'liked_by': [],
                    'likes': 0
                }
            },
            upsert=True
        )
 return list(mongo.db.articles.find())

def get_user_preferences(username):
    user = mongo.db.users.find_one({'username': username})
    if not user:
        return []
    
    # Find all articles that have time spent recorded for this user
    # We query for articles where `time_spent.username` exists.
    # Replace `username` with the actual username field logic if needed.
    query = {f"time_spent.{username}": {"$exists": True}}
    user_articles = mongo.db.articles.find(query)

    category_scores = {}
    for article in user_articles:
        if 'category' in article and article['category']:
            # Extract the time spent by this user
            user_time = article['time_spent'].get(username, 0)
            # Accumulate time spent per category
            category = article['category']
            category_scores[category] = category_scores.get(category, 0) + user_time

    # Sort categories by total time spent, descending
    sorted_preferences = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
    # Extract just the category names
    return [category for category, score in sorted_preferences]



def recommend_articles(username):
    preferences = get_user_preferences(username)

    user = mongo.db.users.find_one({'username': username})
    if not user:
        return []

    user_id = user['_id']
    # If you're still using `user_behavior` or `liked_by` arrays to exclude already-interacted articles,
    # fetch the set of interacted_article_ids or URLs as before.
    # For example:
    interacted_article_ids = [doc['article_id'] for doc in mongo.db.user_behavior.find({'user_id': user_id})]

    recommendations = []
    for category in preferences:
        articles = mongo.db.articles.find({
            'category': category,
            '_id': {'$nin': interacted_article_ids}
        }).limit(5)
        recommendations.extend(list(articles))

    return recommendations

# Function to fetch and store new news, then emit the update to SocketIO
def fetch_and_store_news():
    print("Fetching and storing news...")
    news = fetch_news()
    print("Number of articles returned:", len(news))
    for n in news:
        print("Article URL:", n.get('url'))

    # Convert _id to string
    for article in news:
        article['_id'] = str(article['_id'])

    socket.emit('news_feed_update', {'articles': news})


def categorize_article(article):
    keywords_to_category = {
        'technology': ['tech', 'software', 'AI', 'gadget'],
        'sports': ['football', 'cricket', 'soccer', 'Olympics'],
        'politics': ['election', 'government', 'policy'],
        'health': ['medicine', 'health', 'fitness', 'disease'],
        'business': ['business', 'market', 'stocks', 'finance']
    }
    content = f"{article.get('title', '')} {article.get('description', '')}".lower()
    for category, keywords in keywords_to_category.items():
        if any(keyword in content for keyword in keywords):
            return category
    return 'general'  # Default category


# Scheduler to fetch and store news every 1 minutes
scheduler = BackgroundScheduler()
scheduler.add_job(func=fetch_and_store_news, trigger="interval", minutes=1)
scheduler.start()

if __name__ == '__main__':
    socket.run(app, debug=False, use_reloader=False)
