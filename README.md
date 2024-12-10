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
