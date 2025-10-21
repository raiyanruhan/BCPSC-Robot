from langdetect import detect, detect_langs
text = f"{will-come-form-other-module}"
print(detect(text))  # Likely output: 'en'

# Get probabilities for top languages
print(detect_langs(text)) 