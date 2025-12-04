import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import cv2
import numpy as np
import pickle
import base64
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_embedder = None

FACE_DETECTION_THRESHOLD = 0.5
FACE_RECOGNITION_THRESHOLD = 1.0

def get_embedder():
    global _embedder
    if _embedder is None:
        from keras_facenet import FaceNet
        _embedder = FaceNet()
        logger.info("FaceNet model loaded")
    return _embedder

def get_face_embedding(image_path):
    embedder = get_embedder()
    img = cv2.imread(image_path)
    if img is None:
        logger.warning(f"Cannot read image: {image_path}")
        return None
    
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    for threshold in [FACE_DETECTION_THRESHOLD, 0.3, 0.2]:
        detections = embedder.extract(rgb, threshold=threshold)
        if len(detections) > 0:
            logger.info(f"Face detected with threshold {threshold}")
            return detections[0]['embedding']
    
    logger.warning(f"No face detected in: {image_path}")
    return None

def get_face_embedding_from_array(img_array):
    embedder = get_embedder()
    if img_array is None:
        logger.warning("Input image is None")
        return None
    
    rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
    
    for threshold in [FACE_DETECTION_THRESHOLD, 0.3, 0.2, 0.1]:
        detections = embedder.extract(rgb, threshold=threshold)
        logger.info(f"Camera detection with threshold {threshold}: {len(detections)} face(s)")
        if len(detections) > 0:
            if len(detections) > 1:
                largest = max(detections, key=lambda d: d['box'][2] * d['box'][3])
                return largest['embedding']
            return detections[0]['embedding']
    
    logger.warning("No face detected from camera")
    return None

def compare_faces(embedding1, embedding2, threshold=None):
    if threshold is None:
        threshold = FACE_RECOGNITION_THRESHOLD
    
    if embedding1 is None or embedding2 is None:
        return False, None
    
    distance = float(np.linalg.norm(np.array(embedding1) - np.array(embedding2)))
    is_match = distance < threshold
    
    logger.info(f"Distance: {distance:.4f}, Threshold: {threshold}, Match: {is_match}")
    
    return is_match, distance

def extract_embedding_from_image(image_path):
    try:
        logger.info(f"Extracting from: {image_path}")
        embedding = get_face_embedding(image_path)
        
        if embedding is None:
            return None, "No face detected in image"
        
        return embedding, None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None, str(e)

def extract_embedding_from_base64(base64_data):
    try:
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]
        
        image_bytes = base64.b64decode(base64_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return None, "Cannot decode image"
        
        logger.info(f"Camera image: {img.shape}")
        
        embedding = get_face_embedding_from_array(img)
        
        if embedding is None:
            return None, "No face detected"
        
        return embedding, None
    except Exception as e:
        logger.error(f"Base64 error: {e}")
        return None, str(e)

def save_encoding(embedding, user_id, encoding_dir='face_encodings'):
    os.makedirs(encoding_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"user_{user_id}_{timestamp}.pkl"
    filepath = os.path.join(encoding_dir, filename)
    
    with open(filepath, 'wb') as f:
        pickle.dump(embedding, f)
    
    logger.info(f"Saved encoding: {filepath}")
    return filepath

def load_encoding(filepath):
    try:
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        logger.error(f"Load encoding error: {e}")
        return None

def recognize_face(embedding, users_with_faces, threshold=None):
    if threshold is None:
        threshold = FACE_RECOGNITION_THRESHOLD
    
    if embedding is None:
        return None, None, None, float('inf')
    
    best_match = None
    best_distance = float('inf')
    
    logger.info(f"Comparing with {len(users_with_faces)} users")
    
    for user in users_with_faces:
        db_embedding = load_encoding(user['face_encoding_path'])
        if db_embedding is None:
            continue
        
        is_match, distance = compare_faces(embedding, db_embedding, threshold)
        
        logger.info(f"User {user['username']}: distance={distance:.4f}")
        
        if distance is not None and distance < best_distance:
            best_distance = distance
            best_match = user
    
    if best_match and best_distance < threshold:
        logger.info(f"MATCHED: {best_match['username']} (distance: {best_distance:.4f})")
        return best_match['id'], best_match['username'], best_match['full_name'], best_distance
    
    logger.info(f"NO MATCH: best distance {best_distance:.4f} >= threshold {threshold}")
    return None, None, None, best_distance

def register_face_from_photo(photo_path, user_id, encoding_dir='face_encodings'):
    logger.info(f"Registering face for user {user_id}")
    
    embedding, error = extract_embedding_from_image(photo_path)
    
    if error:
        return None, error
    
    encoding_path = save_encoding(embedding, user_id, encoding_dir)
    return encoding_path, None

def quick_compare(img1, img2, threshold=1.0):
    emb1 = get_face_embedding(img1)
    emb2 = get_face_embedding(img2)
    is_match, distance = compare_faces(emb1, emb2, threshold)
    print(f"Distance: {distance:.4f} | Match: {'YES' if is_match else 'NO'}")
    return is_match, distance

def test_image(image_path):
    print(f"\nTesting: {image_path}")
    print("-" * 40)
    embedding = get_face_embedding(image_path)
    if embedding is not None:
        print(f"SUCCESS: Face detected")
        print(f"Embedding shape: {np.array(embedding).shape}")
    else:
        print("FAILED: No face detected")
    return embedding

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_image(sys.argv[1])
    else:
        print("Usage: python model.py <image_path>")
