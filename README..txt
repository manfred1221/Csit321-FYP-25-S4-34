# README.txt
# Dependencies for Security Officer Face Verification System

# 1. Python version
Python 3.9+ (recommended)

# 2. Flask and related libraries
pip install Flask
pip install Flask-Cors            # if using CORS
pip install Flask-SQLAlchemy      # ORM
pip install Flask-Migrate         # optional for DB migrations

# 3. Database
# PostgreSQL driver for SQLAlchemy
pip install psycopg2-binary

# 4. Numerical and ML libraries
pip install numpy
pip install scikit-learn          # for cosine similarity or other ML utilities
pip install opencv-python         # for webcam access and image processing
pip install tensorflow            # for FaceNet or embedding models (if using TensorFlow)
# OR
pip install torch torchvision      # if using PyTorch-based embeddings

# 5. Base64 handling (usually standard library)
# (No extra installation required for base64 in Python)

# 6. Optional
pip install python-dotenv         # for environment variables
pip install requests              # for API requests from backend scripts
pip install pandas                # if needed for any CSV/data handling

# 7. Frontend (HTML/JS) dependencies
# None needed for plain HTML/JS, all modern browsers support fetch and video API

# 8. Check installation
python -m pip list                # to verify all packages installed
