import cv2

# Replace with your phone's IP camera URL
url = "http://192.168.0.101:4747/video"
cap = cv2.VideoCapture(url)

if not cap.isOpened():
    print("Failed to connect to phone camera!")
    exit()

print("Connected! Press 'q' to quit.")
while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break
    cv2.imshow("Phone Camera Preview", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
