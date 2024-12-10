# Live News Feed Website

A dynamic live news feed website built using Flask, MongoDB, and integrated with BERT for semantic search, recommendations, and more. This project allows users to explore personalized news articles, interact with recommendations, and leverage advanced features powered by machine learning.

---

## Features

- **User Authentication**: Register, log in, and manage sessions securely.
- **Personalized Recommendations**: Suggested articles based on user interaction and preferences.
- **Semantic Search**: Search for articles using natural language powered by BERT.
- **Live News Updates**: Regularly fetch news from external APIs (e.g., NewsAPI) and display the latest articles.
- **User Interactions**: Like articles, track reading time, and store contextual data for personalization.
- **BERT Integration**: Generate semantic embeddings for articles to enable advanced search and recommendations.

---

## Technologies Used

- **Backend**:
  - Python (Flask)
  - Flask extensions: `Flask-PyMongo`, `Flask-SocketIO`, `Flask-CORS`
- **Database**:
  - MongoDB Atlas
  - Collections: `articles`, `users`, `recommendations`, `user_behavior`, `contextual_data`
- **Machine Learning**:
  - Hugging Face Transformers (BERT)
  - PyTorch
- **Frontend**:
  - HTML/CSS (Bootstrap 5)
  - JavaScript (Socket.IO for real-time updates)
- **External APIs**:
  - NewsAPI for fetching news articles

---

## Setup Instructions

Follow these steps to set up the project locally:

### Prerequisites

1. Python 3.11+ (Recommended to use [pyenv](https://github.com/pyenv/pyenv) for version management)
2. MongoDB Atlas account (for database setup)
3. API key for [NewsAPI](https://newsapi.org/)

### Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/<your-username>/<your-repo-name>.git
   cd <your-repo-name>

### Deployment Instructions
a. Deployment to a Local Environment

    Clone the Repository:

git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>

Install Dependencies: Create a virtual environment and install requirements:

python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
pip install -r requirements.txt

Configure Environment Variables: Create a .env file in the project root and add:

MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/news_feed
SECRET_KEY=your-secret-key
NEWS_API_KEY=your-newsapi-key

Run the Application:

python app.py

Access the Application: Open your browser and navigate to:

    http://127.0.0.1:5000

b. Deployment to a Cloud Platform (e.g., Heroku, AWS, or Render)

    Prepare the Environment:
        Ensure all dependencies in requirements.txt are listed.
        Add a Procfile for Heroku:

        web: python app.py

    Push to Cloud: Follow the deployment steps specific to the cloud platform.

### Instructions to Run the Application
Local Execution

    Start the application:

python app.py

The app will be available at:

    http://127.0.0.1:5000

Using the Application

    Login/Registration: Register as a new user or log in with existing credentials.
    View Top News: Explore the latest articles on the homepage.
    Search: Use the search bar to find articles using natural language queries.
    Like Articles: Click the "Like" button to interact with articles.
    Recommendations: View personalized article recommendations under the "Recommended For You" section.
