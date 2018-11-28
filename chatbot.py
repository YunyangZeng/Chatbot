import sys
import pyttsx3
import random
from pydub import AudioSegment
from wxpy import *
from io import BytesIO
from rasa_nlu.training_data import load_data
from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Trainer
from rasa_nlu import config
import spacy
import pandas as pd
from sklearn.svm import SVC
from iexfinance import Stock
import requests
import speech_recognition as sr
r = sr.Recognizer()      
engine=pyttsx3.init()
dictionary={'company':None,'function':None}
pending=0
pending_action=None
INIT,SPECIFY_COMPANY,SPECIFIED,FOUND,NOTFOUND,END=0,1,2,3,4,5
state=INIT
AudioSegment.converter = r"C:\ffmpeg\bin\ffmpeg.exe"
AudioSegment.ffmpeg = r"C:\ffmpeg\bin\ffmpeg.exe"
AudioSegment.ffprobe = r"C:\ffmpeg\bin\ffprobe.exe"
'''training for entity extraction'''
def entity_train():
    nlp = spacy.load('en_core_web_md')
    clf = SVC()
    # Fit the classifier using the training data
    X_train = pd.read_csv('entity_training/X_train.csv')
    y_train = pd.read_csv('entity_training/y_train.csv')['label']
    clf.fit(X_train, y_train)
    return nlp
'''training for interpreter'''
def interpreter_train():
     # Create a trainer
    trainer = Trainer(config.load("/training_data/nlu_config.yml"))
    # Load the training data
    training_data = load_data('/training_data/nlu.json')
    # Create an interpreter by training the model
    interpreter = trainer.train(training_data)
    return interpreter
   
'''Greeting'''
def greeting():
    greeting=("Hi, I am chatbotx, What can I do for you? :)",
             "Hello, my name is chatbotx, is there anything I can help?")    
    grt=random.choice(greeting)
    return grt

'''extract entities'''   
def extract_entities(nlp,message):
    include_entities = ['DATE', 'ORG', 'PERSON']
    # Create a dict to hold the entities
    ents = dict.fromkeys(include_entities)
    # Create a spacy document
    doc = nlp(message)
    for ent in doc.ents:
        if  ent.label_ in include_entities:
            # Save interesting entities
            ents[ent.label_] = ent.text
    return ents 
'''Interprete the usersanswer'''
def interprete(interpreter,message):
    intp=interpreter.parse(message)
    return intp
'''fuctions to catch users' words and return in a certain form:'''
def get_usersanswer():
    user_message=speech_recog()
    user_template = "USER : {0}"
    usersanswer=user_template.format(user_message)
    print(usersanswer)
    return user_message
'''function to return chatbotanswer in a certain form'''
def get_chatbotanswer(message):
    chatbot_template="BOT : {0}"
    chatbotanswer=chatbot_template.format(message)
    return chatbotanswer
'''pending actions according to pending type'''
def pending_actions():
    dic={0:'Which company are you asking? Please say "The name is...".',
     1:'What would you like to ask?',     
     2:'I dont understand.' ,
     3:'What do you want to ask about this company?'
     }
    return dic
'''actions at each state'''
def state_change_action(state):
    dic={ 0:'',   
     1:'Which company are you asking? Please say "The name is..."',
     2:"Company specified",
     4:"Sorry, I cannot find that information",
     3:"Ok, I have found it."     
     }
    answer=dic[state]
    return answer

'''if there is an error when searching skip the error.'''
def error_check1(CPN):
    try:
        p_CPN=CPN.get_price()
    except Exception:
        error='information of company not found'
        return error
    else:
        return 1
def error_check2(CPN):
    try:
        mv_CPN=CPN.get_volume()
    except Exception:
        error='information of company not found'
        return error
    else:
        return 1        
def error_check3(CPN):
    try:
        mc_CPN=CPN.get_market_cap()
    except Exception:
        error='information of company not found'
        return error
    else:
        return 1   
    
'''bot reply under each state and pending combination'''
def bot_reply(intent,state,pending,Org,pending_action,d):
    if state==0:#INIT
        if intent in 'bcd' and Org is not None:
          
            pending,pending_action,state=0,None,2
            d['company'],d['function']=Org,intent
        elif intent in 'bcd' and Org is None:
            pending,pending_action,state=0,None,1
            d['company'],d['function']=Org,intent     
        elif intent not in 'bcd' and Org is not None:
            d['company'],d['function']=Org,None
            pending,pending_action,state=1,3,2
        else:
            pending,pending_action,state=1,1,0
            d['company'],d['function']=None,None
    elif state==1:#Specify company
        if (intent=='h') and (d['company'] is None) and (Org is not None):
            pending,pending_action,state=0,None,2
            d['company']=Org
          
        elif intent=='h' and d['company'] is not None :
            pending,pending_action,state=0,None,2          
            
        elif intent in 'bcd'and Org is not None:
            pending,pending_action,state=0,None,2
            d['company']=Org
            d['function']=intent
        elif intent=='e'or'f'or'i':
            pending,pending_action,state=1,2,1       
    elif state==2:#company specified      
        if intent in 'bcd':
            if Org is not None:#
                pending,pending_action,state=0,None,1
                d['company']=Org
                d['function']=intent            
            elif d['company'] is not None and d['function'] is None and Org is None:#Company specified but question not specified
                pending,pending_action,state=0,None,2
                d['function']=intent    

            
    elif state==3:#information found
        if intent=='j':
            state=5
        elif intent=='i':
            pending,pending_action,state=1,1,0
            d['company']=None
            d['function']=None
        elif intent in 'bcd'and Org is None:
            pending,pending_action,state=0,None,1
            d['company'],d['function']=Org,intent
        elif intent in 'bcd' and Org is not None:
            pending,pending_action,state=0,None,2
            d['company'],d['function']=Org,intent
        else:
            pending,pending_action,state=1,1,0
            d['company'],d['function']=None,None
    return d,pending,pending_action,state
'''convert the company name to stock ticker symbol(useing yahoo finance)'''
def get_ticker_symbol(name):
    url = "http://d.yimg.com/autoc.finance.yahoo.com/autoc?query={}&region=1&lang=en".format(name)
    result = requests.get(url).json()
    for x in result['ResultSet']['Result']:
        if x is not None:
            return x['symbol']
        else:
            return 0
'''ckeck if the entity is an orgnization'''    
def Check_Org(entities):
    if entities['ORG'] is not None:
        print(entities['ORG'])
    return entities['ORG']
'''assign each intent to a letter and return the letter symbol of user's intent '''
def check_intents(intent):
    intents=[['a','greet'],['b','price search'],[
             'c','trading volume search'],['d','market value search'],
             ['e','appreciate'],['f',None],['g','quit'],['h','specify company'],
             ['i','confirm'],['j','deny']]
    for i in intents:
        if i[1]==intent:
            return i[0]   
'''check whether user sends a txt or recording and return a string of what user says'''
def txt_recog(msg):
    print(msg)
    #if user sends a recording then do speech recognition
    if msg.type =='Recording':
        audio = AudioSegment.from_mp3(BytesIO(msg.get_file()))
        export = audio.export("D:/wx/file.wav", format="wav", bitrate="12.20k")#change the path
        AUDIO_FILE = 'D:\\wx\\file.wav'#The same path as above
        userspeech='NA'
        with sr.AudioFile(AUDIO_FILE) as source:
            print('say something')
            audio = r.record(source)  # read the entire audio file
        try:
            userspeech=r.recognize_google(audio)
            print("Google Speech Recognition thinks you said " + userspeech)  
            
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
            
        except sr.RequestError as e:
            print("Could not request results from Google Speech Recognition service")
        return userspeech
    #if user sends a txt then return it directly
    elif msg.type == 'Text':
        return msg.text
         
if __name__ == "__main__":    
    nlp=entity_train()    
    interpreter=interpreter_train()    
    INIT,SPECIFY_COMPANY,SPECIFIED,FOUND,NOTFOUND,END=0,1,2,3,4,5#numerical representation of state
    state=INIT
    bot = Bot()
    my_friend = bot.friends().search('name')[0]#type in the name of your friend 
    my_friend.send(get_chatbotanswer(greeting()))  
    @bot.register(my_friend)
    def chat(msg):
        global dictionary,pending,pending_action,state,my_friend
        print(msg)              
        usermessage=txt_recog(msg)         
        if usermessage=='quit':
            my_friend.send(get_chatbotanswer('See you.'))
            sys.exit()
        intent=interprete(interpreter,usermessage)['intent']['name']
        entities=extract_entities(nlp,usermessage)
        Org=Check_Org(entities)
        intent_=(check_intents(intent))       
        dictionary,pending,pending_action,state=bot_reply(intent_,state,pending,Org,pending_action,dictionary)  
        if state==END:
            my_friend.send(get_chatbotanswer('See you.'))
            sys.exit()        
        action=pending_actions()       
        if pending is not 0:
            my_friend.send(get_chatbotanswer(action[pending_action])) 
        if state is not 0 and state is not 3 and state is not 5:
            my_friend.send(get_chatbotanswer(state_change_action(state)))
        if (dictionary['function'] is not None) and (dictionary['company']is not None):
            CPN=Stock(get_ticker_symbol(dictionary['company']))
            if dictionary['function']=='b':               
                if error_check1(CPN)==1:      
                    p_CPN=CPN.get_price()
                    state=FOUND
                    my_friend.send(get_chatbotanswer('Ok,I have found it! The price of {0} is {1}$'.format(dictionary['company'],p_CPN) ))
                else:     
                    my_friend.send(get_chatbotanswer('Information of company not found'))
                    state=NOTFOUND
            if dictionary['function']=='c':
                if error_check2(CPN)==1:                
                    mv_CPN=CPN.get_volume()
                    my_friend.send(get_chatbotanswer('Ok,I have found it!'))
                    state=FOUND
                    my_friend.send(get_chatbotanswer('The volume of {0} is {1}'.format(dictionary['company'],mv_CPN) ))
                else: 
                    
                    my_friend.send(get_chatbotanswer('Information of company not found'))
                    state=NOTFOUND            
            if dictionary['function']=='d':
                if error_check3(CPN)==1:                
                    mc_CPN=CPN.get_market_cap()
                    my_friend.send(get_chatbotanswer('Ok,I have found it!'))
                    state=FOUND
                    my_friend.send(get_chatbotanswer('The market value of {0} is {1}$'.format(dictionary['company'],mc_CPN)))  
                else:                    
                    my_friend.send(get_chatbotanswer('Information not found'))
                    state=NOTFOUND
        if state == FOUND or state==NOTFOUND :
            my_friend.send(get_chatbotanswer('Do you have other questions? Say "quit" to quit'))
            state=INIT
    
            
