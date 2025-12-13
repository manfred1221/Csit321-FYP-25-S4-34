import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import cv2
import numpy as np
import base64
import logging
from datetime import datetime
from psycopg2.extras import RealDictCursor
from db import get_db_connection
import sys
from keras_facenet import FaceNet


logger = logging.getLogger(__name__)

_embedder = None

FACE_DETECTION_THRESHOLD = 0.5
FACE_RECOGNITION_THRESHOLD = 1.0

def get_embedder():
    global _embedder
    if _embedder is None:
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
    
    # Convert to numpy arrays if needed
    emb1 = np.array(embedding1)
    emb2 = np.array(embedding2)
    
    distance = float(np.linalg.norm(emb1 - emb2))
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

def save_embedding_to_db(embedding, reference_id, user_type='resident'):
    """Save face embedding to database"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Convert embedding to list for PostgreSQL vector type
        embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else list(embedding)
        
        logger.info(f"Embedding dimensions: {len(embedding_list)}")
        logger.info(f"Saving for reference_id={reference_id}, user_type={user_type}")
        
        # Format as PostgreSQL vector string
        embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'
        
        # First verify the reference_id exists in residents table
        cursor.execute("SELECT resident_id FROM residents WHERE resident_id = %s", (reference_id,))
        check_result = cursor.fetchone()
        if not check_result:
            raise ValueError(f"reference_id {reference_id} does not exist in residents table")
        
        cursor.execute("""
            INSERT INTO face_embeddings (user_type, reference_id, embedding)
            VALUES (%s, %s, %s::vector)
            RETURNING embedding_id
        """, (user_type, reference_id, embedding_str))
        
        result = cursor.fetchone()
        if not result:
            raise ValueError("INSERT did not return embedding_id")
        
        embedding_id = result['embedding_id']
        
        conn.commit()
        logger.info(f"Saved embedding to database: embedding_id={embedding_id}")
        return embedding_id
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error saving embedding to database: {type(e).__name__}: {e}")
        raise ValueError(f"Database error: {type(e).__name__}: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def load_embedding_from_db(embedding_id):
    """Load face embedding from database"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT embedding FROM face_embeddings WHERE embedding_id = %s
        """, (embedding_id,))
        result = cursor.fetchone()
        if result and result['embedding']:
            # Convert from PostgreSQL vector to numpy array
            embedding = np.array(result['embedding'])
            return embedding
        return None
    except Exception as e:
        logger.error(f"Error loading embedding from database: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_all_embeddings():
    """Get all face embeddings with user info"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT fe.embedding_id, fe.user_type, fe.reference_id, fe.embedding,
                   r.full_name, r.unit_number
            FROM face_embeddings fe
            LEFT JOIN residents r ON fe.reference_id = r.resident_id AND fe.user_type = 'resident'
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()

def recognize_face(embedding, threshold=None):
    """
    Recognize face by comparing with database embeddings
    
    Returns:
        tuple: (resident_id, full_name, full_name, distance) or (None, None, None, distance)
    """
    if threshold is None:
        threshold = FACE_RECOGNITION_THRESHOLD
    
    if embedding is None:
        return None, None, None, float('inf')
    
    # Get all embeddings from database
    all_embeddings = get_all_embeddings()
    
    best_match = None
    best_distance = float('inf')
    
    logger.info(f"Comparing with {len(all_embeddings)} embeddings")
    
    for record in all_embeddings:
        db_embedding = record.get('embedding')
        if db_embedding is None:
            continue
        
        # Convert to numpy array if needed
        if not isinstance(db_embedding, np.ndarray):
            db_embedding = np.array(db_embedding)
        
        is_match, distance = compare_faces(embedding, db_embedding, threshold)
        
        logger.info(f"Reference {record['reference_id']} ({record.get('full_name', 'Unknown')}): distance={distance:.4f}")
        
        if distance is not None and distance < best_distance:
            best_distance = distance
            best_match = record
    
    if best_match and best_distance < threshold:
        logger.info(f"MATCHED: {best_match.get('full_name', 'Unknown')} (distance: {best_distance:.4f})")
        return (
            best_match['reference_id'],
            best_match.get('full_name', 'Unknown'),
            best_match.get('full_name', 'Unknown'),
            best_distance
        )
    
    logger.info(f"NO MATCH: best distance {best_distance:.4f} >= threshold {threshold}")
    return None, None, None, best_distance

def recognize_face_with_users(embedding, users_with_faces, threshold=None):
    """
    Recognize face using provided user list (for backward compatibility)
    
    Args:
        embedding: Face embedding to match
        users_with_faces: List of user dicts with 'embedding' field
        threshold: Recognition threshold
    """
    if threshold is None:
        threshold = FACE_RECOGNITION_THRESHOLD
    
    if embedding is None:
        return None, None, None, float('inf')
    
    best_match = None
    best_distance = float('inf')
    
    logger.info(f"Comparing with {len(users_with_faces)} users")
    
    for user in users_with_faces:
        db_embedding = user.get('embedding')
        if db_embedding is None:
            continue
        
        # Convert to numpy array if needed
        if not isinstance(db_embedding, np.ndarray):
            db_embedding = np.array(db_embedding)
        
        is_match, distance = compare_faces(embedding, db_embedding, threshold)
        
        logger.info(f"User {user.get('username', user.get('full_name', 'Unknown'))}: distance={distance:.4f}")
        
        if distance is not None and distance < best_distance:
            best_distance = distance
            best_match = user
    
    if best_match and best_distance < threshold:
        logger.info(f"MATCHED: {best_match.get('full_name', 'Unknown')} (distance: {best_distance:.4f})")
        return (
            best_match.get('id', best_match.get('resident_id')),
            best_match.get('username', best_match.get('full_name')),
            best_match.get('full_name'),
            best_distance
        )
    
    logger.info(f"NO MATCH: best distance {best_distance:.4f} >= threshold {threshold}")
    return None, None, None, best_distance

def register_face_from_photo(photo_path, reference_id, user_type='resident'):
    """
    Register face from photo and save to database
    
    Args:
        photo_path: Path to photo file
        reference_id: resident_id or visitor_id
        user_type: 'resident' or 'visitor'
    
    Returns:
        tuple: (embedding_id, error_message)
    """
    logger.info(f"Registering face for {user_type} {reference_id} from {photo_path}")
    
    # Check if photo exists
    if not os.path.exists(photo_path):
        return None, f"Photo file not found: {photo_path}"
    
    embedding, error = extract_embedding_from_image(photo_path)
    
    if error:
        logger.error(f"Embedding extraction failed: {error}")
        return None, error
    
    if embedding is None:
        return None, "Failed to extract embedding (returned None)"
    
    logger.info(f"Embedding extracted successfully, shape: {np.array(embedding).shape}")
    
    try:
        embedding_id = save_embedding_to_db(embedding, reference_id, user_type)
        logger.info(f"Face registered successfully: embedding_id={embedding_id}")
        return embedding_id, None
    except ValueError as e:
        logger.error(f"ValueError in save_embedding_to_db: {e}")
        return None, str(e)
    except Exception as e:
        logger.error(f"Unexpected error in save_embedding_to_db: {type(e).__name__}: {e}")
        return None, f"{type(e).__name__}: {str(e)}"

def update_face_embedding(embedding_id, new_embedding):
    """Update existing face embedding"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        embedding_list = new_embedding.tolist() if isinstance(new_embedding, np.ndarray) else list(new_embedding)
        embedding_str = '[' + ','.join(map(str, embedding_list)) + ']'
        
        cursor.execute("""
            UPDATE face_embeddings SET embedding = %s::vector
            WHERE embedding_id = %s
        """, (embedding_str, embedding_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error updating embedding: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def delete_face_embedding(embedding_id):
    """Delete face embedding from database"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM face_embeddings WHERE embedding_id = %s", (embedding_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting embedding: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

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
    if len(sys.argv) > 1:
        test_image(sys.argv[1])
    else:
        print("Usage: python model.py <image_path>")