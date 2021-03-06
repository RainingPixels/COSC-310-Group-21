# imports
import nltk                                     # used to tokenize and lemmatize sentences
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
import pickle
import numpy as np
from keras.models import load_model             # used as the deep learning model to handle bag of words
import json
import random
import tkinter                                  # used to build user interface
from tkinter import *
from regex import F
import spacy
from spacy import displacy


#Google Translate API 
from googletrans import Translator
translator = Translator()

#Wikipedia API integration
import wikipediaapi
wiki_wiki = wikipediaapi.Wikipedia('en')



# load the trained model and pickle files
intents = json.loads(open('app/chatbot/data/intents.json').read())
model = load_model('app/chatbot/models/trained_chatbot_model.h5')
words = pickle.load(open('app/chatbot/data/words.pkl', 'rb'))
classes = pickle.load(open('app/chatbot/data/classes.pkl', 'rb'))


# spacy 'brain'
nlp = spacy.load('en_core_web_sm')
nlp.add_pipe('merge_entities')


# POS Mapper Function (used to ensure POS compatibility with lemmatizer)
def get_pos(word):
    tag = nltk.pos_tag([word])
    tag = tag[0][1][0].upper()
    dict = {"J": wordnet.ADJ,
            "N": wordnet.NOUN,
            "V": wordnet.VERB,
            "R": wordnet.ADV }

    return dict.get(tag, wordnet.NOUN)


# function that tokenizes, lemmatizes, and lowercases an input sentence
def clean_up_sentence(sentence):
    lemmatizer = WordNetLemmatizer()
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(word.lower(), get_pos(word.lower())) for word in sentence_words]
    return sentence_words

# named entity recognition
def ner(sentence):
    doc = nlp(sentence)
    sen = " ".join([t.text if not t.ent_type_ else t.ent_type_ for t in doc])
    return sen.replace('PERSON', 'John').replace('GPE', 'Canada').replace('ORG', 'Microsoft').replace('CARDINAL', 'three')


# function that returns a bag of words for the input sentence 
def bow(sentence, words, show_details=True):
    
    #search for difficult to recognize named entities
    sentence_words = ner(sentence)
    
    # tokenize the pattern/sentence
    sentence_words = clean_up_sentence(sentence_words)
    
    # create bag of words
    bag = [0]*len(words) 
    for s in sentence_words:
        for i,w in enumerate(words):
            if w == s: 
                # assign 1 if current word is in the vocabulary position
                bag[i] = 1
                if show_details:
                    print ("found in bag: %s" % w)
    
    return(np.array(bag))


# function that returns the probability of the classes given an input sentence and model
def predict_class(sentence, model):
    
    # gets bag of words and predicts classes
    bag = bow(sentence, words,show_details=False)
    res = model.predict(np.array([bag]))[0]
   
    # filters out class predictions that fall beneath a certain threshold
    THRESHOLD = 0.25
    results = [[i,r] for i,r in enumerate(res) if r>THRESHOLD]
   
    # sort by strength of probability
    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append({"class": classes[r[0]], "probability": str(r[1])})
    
    return return_list


# function that returns a random response from the json file based on what the predicted class is 
def getResponse(predicted_classes, intents_json):
    tag = predicted_classes[0]['class']
    list_of_intents = intents_json['intents']
    for i in list_of_intents:
        if(i['tag']== tag):
            result = random.choice(i['responses'])
            break
    
   #Wikipedia API integration. Give definition of possible mental health disorders. 
   #Searches wikipedia based on tag iff tag is a mental health disorder
    if tag == 'major_depression' or tag == 'anxiety' or tag == 'positive disorganization' :
       
        wikiTag = ''

        #form wikiTag
        if tag == 'major_depression':
            wikiTag = "depression"
        elif tag == 'anxiety':
            wikiTag = "anxiety"
        elif tag == 'positive disorganization':
            wikiTag += "schizophrenia"

        #Retrieve subject 
        page_py = wiki_wiki.page(wikiTag)

        #create string for returning 
        str = "\n\nHere is a summary and link:\n" + page_py.summary[0:120] + "\n" + page_py.fullurl

        #return what the chatbot will say plus wikipedia information
        return result + str
    
    else:
        #otherwise, return default conversation
        return result


#function that returns which language the inputted sentence is in 
def which_language(text):
    translated = translator.translate(text)
    return translated.src

# function that returns a chatbot response given an input sentence
def chatbot_response(text):

    #Google translate API integration
    if which_language(text) != 'en':
        translated = translator.translate(text)
        translated_sentence = translated.text
        translated_language = translated.src

        predicted_classes = predict_class(translated_sentence, model)
        #res = getResponse(predicted_classes, intents)
        res = getResponse(predicted_classes, intents)
        
        translated_result = translator.translate(res, dest=translated_language)
        #print(translated_result.text)
        return translated_result.text
        
    else:   #language is in english
        predicted_classes = predict_class(text, model)
        #res = getResponse(predicted_classes, intents)
        res = getResponse(predicted_classes, intents)
        return res


        


  

# function that acts as a send button for the user interface
def send():
    msg = EntryBox.get("1.0",'end-1c').strip()
    EntryBox.delete("0.0",END)
    
    if msg != '':
        ChatLog.config(state=NORMAL)
        ChatLog.insert(END, "You: " + msg + '\n\n')
        ChatLog.config(foreground="#442265", font=("Verdana", 12 ))

        res = chatbot_response(msg)
        ChatLog.insert(END, "Psychiatrist: " + res + '\n\n')

        ChatLog.config(state=DISABLED)
        ChatLog.yview(END)


# User interface
base = Tk()
base.title("Psychiatrist Chatbot")
base.geometry("400x500")
base.resizable(width=FALSE, height=FALSE)

# create chatbot window
ChatLog = Text(base, bd=0, bg="grey", height="8", width="50", font="Arial",)
ChatLog.config(state=DISABLED)

# bind scrollbar to Chat window
scrollbar = Scrollbar(base, command=ChatLog.yview, cursor="circle")
ChatLog['yscrollcommand'] = scrollbar.set

# create button to send message
SendButton = Button(base, font=("Arial",14,'bold'), text="Send", width="12", height=5, bd=0, bg="#fe6f5e", activebackground="#3c9d9b",fg='#ffffff', command=send)

# create the box to enter message
EntryBox = Text(base, bd=0, bg="grey",width="29", height="5", font="Arial")
EntryBox.bind("<Return>", send)

# place all the components on the screen
ChatLog.place(x=6,y=6, height=386, width=370)
scrollbar.place(x=376,y=6, height=386)
EntryBox.place(x=128, y=401, height=90, width=265)
SendButton.place(x=6, y=401, height=90)

# continuously run the chat window / user interface
base.mainloop()