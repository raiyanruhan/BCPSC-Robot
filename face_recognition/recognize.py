import cv2
import face_recognition
import os
import json

# --- Load known faces ---
known_faces = []
known_names = []

path = "known_person"
valid_extensions = (".jpg", ".jpeg", ".png")  # only allow image files

for filename in os.listdir(path):
    if filename.lower().endswith(valid_extensions):
        img = face_recognition.load_image_file(os.path.join(path, filename))
        encodings = face_recognition.face_encodings(img)
        if len(encodings) > 0:
            encoding = encodings[0]
            known_faces.append(encoding)
            name = os.path.splitext(filename)[0]  # filename without extension
            known_names.append(name)
            print(f"[INFO] Loaded {filename} as {name}")
        else:
            print(f"[WARN] No faces found in {filename}, skipping.")

# --- Load responses from JSON (if available) ---
if os.path.exists("responses.json"):
    with open("responses.json", "r") as f:
        responses = json.load(f)
else:
    responses = {}

# --- Start webcam (phone stream via IP Webcam app) ---
# Use "0" if you later want to test on a real webcam
video = cv2.VideoCapture("http://192.168.0.101:4747/video")
print("Press 'q' to quit")

while True:
    ret, frame = video.read()
    if not ret:
        print("[ERROR] Failed to grab frame from camera")
        break

    # Convert to RGB for face_recognition
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detect faces
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    for face_encoding, face_location in zip(face_encodings, face_locations):
        matches = face_recognition.compare_faces(known_faces, face_encoding)
        name = "Student"   # Default label for unknown faces

        if True in matches:
            match_index = matches.index(True)
            name = known_names[match_index]

        # Dynamic response
        if name in responses:
            response = responses[name]
        elif name == "Student":
            response = "Hey bro, what up?"
        else:
            response = f"Assalamu Alaikum {name} Sir!"

        print(response)

        # Draw rectangle + label
        top, right, bottom, left = face_location
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.putText(frame, name, (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    cv2.imshow("Face Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

video.release()
cv2.destroyAllWindows()
