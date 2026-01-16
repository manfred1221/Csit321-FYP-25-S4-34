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
from database import get_db_connection
import sys
from keras_facenet import FaceNet


logger = logging.getLogger(__name__)

_embedder = None

FACE_DETECTION_THRESHOLD = 0.3  # More lenient detection
FACE_RECOGNITION_THRESHOLD = 1.2  # More lenient matching

def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = FaceNet()
        logger.info("FaceNet model loaded")
    return _embedder

def get_face_embedding(image_path):
    """Extract face embedding from image file"""
    embedder = get_embedder()
    img = cv2.imread(image_path)
    if img is None:
        logger.warning(f"Cannot read image: {image_path}")
        return None
    
    # Resize if image is too large
    height, width = img.shape[:2]
    max_dimension = 1024
    if max(height, width) > max_dimension:
        scale = max_dimension / max(height, width)
        img = cv2.resize(img, None, fx=scale, fy=scale)
        logger.info(f"Resized image to {img.shape}")
    
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Try multiple thresholds
    for threshold in [0.3, 0.2, 0.1]:
        detections = embedder.extract(rgb, threshold=threshold)
        if len(detections) > 0:
            logger.info(f"Face detected with threshold {threshold}")
            # If multiple faces, use the largest one
            if len(detections) > 1:
                largest = max(detections, key=lambda d: d['box'][2] * d['box'][3])
                return largest['embedding']
            return detections[0]['embedding']
    
    logger.warning(f"No face detected in: {image_path}")
    return None

def get_face_embedding_from_array(img_array):
    """Extract face embedding from numpy array (camera capture)"""
    embedder = get_embedder()
    if img_array is None:
        logger.warning("Input image is None")
        return None
    
    # Ensure image is in correct format
    if len(img_array.shape) == 2:
        # Grayscale to RGB
        img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
    elif img_array.shape[2] == 4:
        # RGBA to RGB
        img_array = cv2.cvtColor(img_array, cv2.COLOR_BGRA2RGB)
    else:
        # BGR to RGB
        img_array = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
    
    logger.info(f"Processing camera image: shape={img_array.shape}, dtype={img_array.dtype}")
    
    # Try multiple thresholds for camera images
    for threshold in [0.3, 0.2, 0.1, 0.05]:
        detections = embedder.extract(img_array, threshold=threshold)
        logger.info(f"Camera detection with threshold {threshold}: {len(detections)} face(s)")
        if len(detections) > 0:
            if len(detections) > 1:
                # Use largest face
                largest = max(detections, key=lambda d: d['box'][2] * d['box'][3])
                logger.info(f"Multiple faces detected, using largest")
                return largest['embedding']
            return detections[0]['embedding']
    
    logger.warning("No face detected from camera")
    return None

def compare_faces(embedding1, embedding2, threshold=None):
    """Compare two face embeddings"""
    if threshold is None:
        threshold = FACE_RECOGNITION_THRESHOLD
    
    if embedding1 is None or embedding2 is None:
        return False, None
    
    # Convert to numpy arrays if needed
    emb1 = np.array(embedding1)
    emb2 = np.array(embedding2)
    
    # Euclidean distance
    distance = float(np.linalg.norm(emb1 - emb2))
    is_match = distance < threshold
    
    logger.info(f"Distance: {distance:.4f}, Threshold: {threshold}, Match: {is_match}")
    
    return is_match, distance

def extract_embedding_from_image(image_path):
    """Wrapper for extracting embedding from file"""
    try:
        logger.info(f"Extracting from: {image_path}")
        embedding = get_face_embedding(image_path)
        
        if embedding is None:
            return None, "No face detected in image. Please ensure:\n- Face is clearly visible\n- Good lighting\n- Front-facing photo\n- No sunglasses or masks"
        
        return embedding, None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None, str(e)

def extract_embedding_from_base64(base64_data):
    """Extract embedding from base64 image (camera capture)"""
    try:
        # Remove data URL prefix if present
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]
        
        # Decode base64 to image
        image_bytes = base64.b64decode(base64_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return None, "Cannot decode image"
        
        logger.info(f"Camera image decoded: shape={img.shape}, dtype={img.dtype}")
        
        # Enhance image quality for better detection
        # Increase contrast
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        logger.info("Image enhanced for better detection")
        
        # Try both original and enhanced
        embedding = get_face_embedding_from_array(enhanced)
        if embedding is None:
            logger.info("Trying original image without enhancement")
            embedding = get_face_embedding_from_array(img)
        
        if embedding is None:
            return None, "No face detected. Please:\n- Move closer to camera\n- Ensure good lighting\n- Face the camera directly\n- Remove sunglasses/masks"
        
        return embedding, None
    except Exception as e:
        logger.error(f"Base64 error: {e}", exc_info=True)
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

        # Verify the reference_id exists in the appropriate table based on user_type
        if user_type == 'resident':
            cursor.execute("SELECT resident_id FROM residents WHERE resident_id = %s", (reference_id,))
            check_result = cursor.fetchone()
            if not check_result:
                raise ValueError(f"reference_id {reference_id} does not exist in residents table")
        elif user_type == 'visitor':
            cursor.execute("SELECT visitor_id FROM visitors WHERE visitor_id = %s", (reference_id,))
            check_result = cursor.fetchone()
            if not check_result:
                raise ValueError(f"reference_id {reference_id} does not exist in visitors table")
        elif user_type in ['ADMIN', 'internal_staff', 'temp_staff', 'security_officer']:
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (reference_id,))
            check_result = cursor.fetchone()
            if not check_result:
                raise ValueError(f"reference_id {reference_id} does not exist in users table")
        # For other user types, skip validation (or add more checks as needed)

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
        logger.info(f"✓ Saved embedding to database: embedding_id={embedding_id}")
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
                   CASE
                       WHEN fe.user_type = 'resident' THEN r.full_name
                       WHEN fe.user_type IN ('ADMIN', 'internal_staff', 'temp_staff', 'security_officer') THEN u.username
                       WHEN fe.user_type = 'visitor' THEN v.full_name
                       ELSE 'Unknown'
                   END as full_name,
                   CASE
                       WHEN fe.user_type = 'resident' THEN r.unit_number
                       ELSE NULL
                   END as unit_number
            FROM face_embeddings fe
            LEFT JOIN residents r ON fe.reference_id = r.resident_id AND fe.user_type = 'resident'
            LEFT JOIN users u ON fe.reference_id = u.user_id AND fe.user_type IN ('ADMIN', 'internal_staff', 'temp_staff', 'security_officer')
            LEFT JOIN visitors v ON fe.reference_id = v.visitor_id AND fe.user_type = 'visitor'
        """)
        results = []
        for row in cursor.fetchall():
            record = dict(row)
            # Use resident_name or user_name, whichever is available
            record['full_name'] = record.get('resident_name') or record.get('user_name') or 'Unknown'
            
            # Parse embedding - comprehensive handling
            embedding = record.get('embedding')
            if embedding is not None:
                try:
                    if isinstance(embedding, str):
                        # Parse string like "[0.1, 0.2, ...]" or "{0.1, 0.2, ...}"
                        embedding_str = embedding.strip('[]{}')
                        if embedding_str:
                            embedding_list = [float(x.strip()) for x in embedding_str.split(',')]
                            record['embedding'] = np.array(embedding_list, dtype=np.float32)
                            logger.debug(f"Parsed string embedding, shape: {record['embedding'].shape}")
                        else:
                            logger.warning(f"Empty embedding string for {record['reference_id']}")
                            record['embedding'] = None
                    elif isinstance(embedding, (list, tuple)):
                        record['embedding'] = np.array(embedding, dtype=np.float32)
                    elif isinstance(embedding, np.ndarray):
                        record['embedding'] = embedding.astype(np.float32)
                    else:
                        # Try generic conversion
                        record['embedding'] = np.array(embedding, dtype=np.float32)
                except Exception as e:
                    logger.error(f"Failed to parse embedding for {record['reference_id']}: {e}")
                    record['embedding'] = None
            
            results.append(record)
        
        logger.info(f"Loaded {len(results)} embeddings from database")
        return results
    finally:
        cursor.close()
        conn.close()

def recognize_face(embedding, threshold=None):
    """
    Recognize face by comparing with database embeddings
    
    Returns:
        tuple: (reference_id, username, full_name, distance) or (None, None, None, distance)
    """
    if threshold is None:
        threshold = FACE_RECOGNITION_THRESHOLD
    
    if embedding is None:
        return None, None, None, float('inf')
    
    # Get all embeddings from database
    all_embeddings = get_all_embeddings()
    
    best_match = None
    best_distance = float('inf')
    
    logger.info(f"Comparing with {len(all_embeddings)} embeddings, threshold={threshold}")
    
    for record in all_embeddings:
        db_embedding = record.get('embedding')
        if db_embedding is None:
            continue
        
        # Convert to numpy array if needed
        if not isinstance(db_embedding, np.ndarray):
            db_embedding = np.array(db_embedding)
        
        is_match, distance = compare_faces(embedding, db_embedding, threshold)
        
        name = record.get('full_name') or record.get('username') or 'Unknown'
        logger.info(f"Reference {record['reference_id']} ({name}): distance={distance:.4f}")
        
        if distance is not None and distance < best_distance:
            best_distance = distance
            best_match = record
    
    if best_match and best_distance < threshold:
        name = best_match.get('full_name') or best_match.get('username') or 'Unknown'
        logger.info(f"✓ MATCHED: {name} (distance: {best_distance:.4f})")
        return (
            best_match['reference_id'],
            best_match.get('username', name),
            name,
            best_distance
        )
    
    logger.info(f"✗ NO MATCH: best distance {best_distance:.4f} >= threshold {threshold}")
    return None, None, None, best_distance

def register_face_from_photo(photo_path, reference_id, user_type='resident'):
    """
    Register face from photo and save to database
    
    Args:
        photo_path: Path to photo file
        reference_id: ID of the user (resident_id, user_id, etc.)
        user_type: 'resident', 'admin', 'staff', 'visitor', etc.
    
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
        logger.info(f"✓ Face registered successfully: embedding_id={embedding_id}")
        return embedding_id, None
    except ValueError as e:
        logger.error(f"ValueError in save_embedding_to_db: {e}")
        return None, str(e)
    except Exception as e:
        logger.error(f"Unexpected error in save_embedding_to_db: {type(e).__name__}: {e}")
        return None, f"{type(e).__name__}: {str(e)}"

def test_image(image_path):
    """Test face detection on an image"""
    print(f"\nTesting: {image_path}")
    print("-" * 40)
    embedding = get_face_embedding(image_path)
    if embedding is not None:
        print(f"✓ SUCCESS: Face detected")
        print(f"Embedding shape: {np.array(embedding).shape}")
    else:
        print("✗ FAILED: No face detected")
    return embedding

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_image(sys.argv[1])
    else:
        print("Usage: python model.py <image_path>")