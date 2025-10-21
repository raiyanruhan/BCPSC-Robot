from flask import Flask, request

app = Flask(__name__)

@app.route("/person", methods=["POST"])
def receive_person():
    data = request.json
    print(f"Received: {data}")  # You can do anything here (save to DB, trigger function, etc.)
    return {"status": "ok", "received": data}

if __name__ == "__main__":
    app.run(port=5000)  # Run on http://127.0.0.1:5000
