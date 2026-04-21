from googletrans import Translator

translator = Translator()

def to_english(text):
    return translator.translate(text, src="ta", dest="en").text

def to_tamil(text):
    return translator.translate(text, src="en", dest="ta").text
print("translator is on")
