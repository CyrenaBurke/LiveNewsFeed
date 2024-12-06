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
        news = fetch_news()  # Top headlines
        recommendations = recommend_articles(username)  # Personalized recommendations

        # Add like status and like count for the main news articles
        for article in news:
            article['liked'] = username in article.get('liked_by', [])
            article['likes'] = len(article.get('liked_by', []))

        # Add like status and like count for the recommended articles
        for rec_article in recommendations:
            rec_article['liked'] = username in rec_article.get('liked_by', [])
            rec_article['likes'] = len(rec_article.get('liked_by', []))

        return render_template('home.html', username=username, news=news, recommendations=recommendations)
    else:
        return redirect(url_for('login'))


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
    data = request.json
    article_url = data.get('url')
    time_spent = data.get('time_spent', 0)

    if not article_url or time_spent <= 0:
        return jsonify({'error': 'Invalid input'}), 400

    # Update the article's behavior tracking for the user
    mongo.db.articles.update_one(
        {'url': article_url},
        {'$inc': {f'behavior_tracking.{username}.time_spent': time_spent}}
    )
    return jsonify({'success': True, 'time_spent': time_spent})


@app.route('/like', methods=['POST'])
def like_article():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 403

    username = session['username']
    article_url = request.json.get('url')

    if not article_url:
        return jsonify({'error': 'Invalid article URL'}), 400

    # Find the article by URL
    article = mongo.db.articles.find_one({'url': article_url})
    if not article:
        return jsonify({'error': 'Article not found'}), 404

    # Check if the user already liked the article
    liked = False
    if username in article.get('liked_by', []):
        # User has already liked the article, so we un-like it
        mongo.db.articles.update_one(
            {'url': article_url},
            {'$pull': {'liked_by': username}}  # Remove user from liked_by list
        )
        liked = False
    else:
        # User hasn't liked the article yet, so we like it
        mongo.db.articles.update_one(
            {'url': article_url},
            {'$addToSet': {'liked_by': username}}  # Add user to liked_by list
        )
        liked = True

        # Update user_behavior collection to track the like
        mongo.db.user_behavior.update_one(
            {'url': article_url},
            {
                '$setOnInsert': {'url': article_url},  # Insert the article if not already present
                '$set': {f'user_.{username}.liked': liked},  # Set the like status for this user
            },
            upsert=True
        )

    # Get the updated article and count the likes
    updated_article = mongo.db.articles.find_one({'url': article_url})
    like_count = len(updated_article.get('liked_by', []))

    # Update the `likes` count in the article
    mongo.db.articles.update_one(
        {'url': article_url},
        {'$set': {'likes': like_count}}  # Update the likes field with the current count
    )

    return jsonify({'liked': liked, 'likes': like_count})


# Function to fetch news from NewsAPI and store in MongoDB if not already stored
def fetch_news():
    params = {
    'apiKey': NEWS_API_KEY,
    'q': 'technology', 
    'pageSize': 20,
    'sortBy': 'publishedAt'
}

    response = requests.get(NEWS_API_URL, params=params)
    print("NewsAPI status code:", response.status_code)
    print("NewsAPI response JSON:", response.json())  # Print the entire JSON
    
    if response.status_code != 200:
        print(f"Error fetching news: {response.status_code}")
        return []

    articles = response.json().get('articles', [])
    print("Number of articles received:", len(articles))

    for article in articles:
        print("Article URL:", article.get('url'))
        article['category'] = categorize_article(article)
        article['liked_by'] = []
        article['likes'] = 0
        article['time_spent'] = {}
        # Use $set so existing documents update, and new ones insert
        mongo.db.articles.update_one(
            {'url': article['url']},
            {'$set': article},
            upsert=True
        )
    return list(mongo.db.articles.find())


def get_user_preferences(username):
    user_behavior = mongo.db.user_behavior.find({'user_': {'$exists': True}})
    category_scores = {}
    for behavior in user_behavior:
        user_data = behavior['user_'].get(username, {})
        time_spent = user_data.get('time_spent', 0)
        # Extract article categories and score
        article = mongo.db.articles.find_one({'url': behavior['url']})
        if article and 'category' in article:
            category = article['category']
            category_scores[category] = category_scores.get(category, 0) + time_spent
    # Sort by highest preference
    sorted_preferences = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
    return [category for category, score in sorted_preferences]


def recommend_articles(username):
    preferences = get_user_preferences(username)
    recommendations = []
    for category in preferences:
        # Find articles matching the user's preferences
        articles = mongo.db.articles.find({
            'category': category,
            'url': {'$nin': [doc['url'] for doc in mongo.db.user_behavior.find({'user_': {username: {'$exists': True}}})]}
        }).limit(5)  # Limit recommendations to avoid overload
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