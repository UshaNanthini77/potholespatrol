# -*- coding: utf-8 -*-
"""
Created on Mon Sep 20 19:30:08 2021

@author: shruthi
"""

from flask import Flask, render_template,request,Response,redirect,send_file,send_from_directory,session
from pymongo import MongoClient
from flask_mongoengine import MongoEngine
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
import cv2
import time
import imutils
import os
from datetime import datetime
import numpy as np
from sklearn.metrics import pairwise
import time
import requests
import json
import geopy
from geopy.geocoders import Nominatim
from tensorflow.keras import Sequential
from keras.models import model_from_json
from keras.models import load_model
from keras.layers import Dense
from keras.layers import Dropout
from keras.utils import np_utils
from bson.objectid import ObjectId
import glob
import tempfile
import pymongo
import ssl
global loadedModel
size = 300


global temp_file


app = Flask(__name__)
app.secret_key = 'pothole patrol'


app.config["MONGO_URI"] = "mongodb+srv://shruthi:2403rose@cluster0.zvstj.mongodb.net/potholepatrol?retryWrites=true&w=majority"
mongo = PyMongo(app,ssl_cert_reqs=ssl.CERT_NONE)
records = mongo.db.potpat
userrecords = mongo.db.users




def predict_pothole(currentFrame):
    loadedModel = load_model('full_model.h5')
    currentFrame = cv2.resize(currentFrame,(size,size))
    currentFrame = currentFrame.reshape(1,size,size,1).astype('float')
    currentFrame = currentFrame/255
    prob = loadedModel.predict_proba(currentFrame)
    max_prob = max(prob[0])
    if(max_prob>.90):
        return loadedModel.predict_classes(currentFrame) , max_prob
    return "none",0

def gen(videofile,username):
   
    cap = cv2.VideoCapture(videofile.name)

    total_frames=cap.get(cv2.CAP_PROP_FRAME_COUNT)
    frameCnt=0
    detected = False
    
    out = cv2.VideoWriter('output.mp4', cv2.VideoWriter_fourcc(*'DIVX'), 20.0, (200,200))
    total_prob = 0
    while(frameCnt < 100):
        frameCnt+=1
        ret, frame = cap.read()
        if ret:
            frame = cv2.resize(frame,(200,200))
            frame = cv2.flip(frame,1)
        
            clone = frame.copy()
        
            (height,width) = frame.shape[:2]
        
            grayClone = cv2.cvtColor(clone,cv2.COLOR_BGR2GRAY)
            
            pothole,prob = predict_pothole(grayClone)
            
            cv2.putText(frame , str(pothole)+' '+str(prob*100)+'%' , (30,30) , cv2.FONT_HERSHEY_DUPLEX , 1 , (0,255,0) , 1)
            
            out.write(cv2.resize(frame, (200,200) ))
            total_prob += prob
            if(pothole == 1):
                detected = True
    
    
    out.release()
    
    
    return total_prob,frameCnt,detected
    
    
@app.route('/home')
def home():
    return render_template('index.html')

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    message = 'Please login to your account'
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        email_found = userrecords.find_one({"email": email})
        if email_found:
            email_val = email_found['email']
            passwordcheck = email_found['password']
            if(email=="potholeadmin@gmail.com" and password=="admin"):
                return redirect('/admin')
            if(passwordcheck == password):
                session['email'] = email_val
                return redirect('/client')
            else:
                message = 'Wrong password'
                return render_template('login.html',message=message)
        else:
            message = 'Email not found'
            return render_template('login.html',message=message)
    return render_template('login.html',message=message)

@app.route('/register', methods=['POST', 'GET'])
def register():
    return render_template('register.html')


@app.route('/reguser', methods=['POST'])
def reguser():
    email = request.form['email']
    pwd = request.form['password']
    name = request.form['name']
    user_reg = {"email": email, "password": pwd, "name": name}
    userrecords.insert_one(user_reg)
    return redirect('/')
    
      
@app.route('/upload', methods=['POST'])
def upload():
    print(lat)
    print(lon)
    username = request.form['name']
    phone = request.form['phone']
    #location = request.form['location']
    date = request.form['date']
    file = request.files['video_select']
    file.filename = username+".mp4"
    comments = request.form['comment']
    severity = request.form['number_people']

    global tfile
    tfile=tempfile.NamedTemporaryFile()
    tfile.write(file.read())
    file.seek(0)
    if "email" in session:
        email = session["email"]
        email_found = userrecords.find_one({"email": email})
        if email_found:
            tprob,tframes,detect = gen(tfile,username)
            avg_prob = tprob/tframes
            res = "yes"
            if(detect == False):
                res = "no"
        #mongo.save_file(file.filename, file)
            records.insert({"email": email, "name": username, "phoneno": phone, "date": date, "videofile": file.filename, "pothole location": loc, "comments": comments, "severity":severity, "accuracy":avg_prob,"pothole detected":res, "status":"pending", "latitude":lat, "longitude":lon})
            f = open('output.mp4','rb')
            dets = records.find().sort("_id", -1).limit(1)
            for det in dets:
                nam = det['_id']
                global savename
                savename = str(nam)
                print(type(savename))
            records.find_one_and_update({"_id": ObjectId(nam)}, {"$set": {"videofile":savename+".mp4"}})
            mongo.save_file(savename+".mp4",f)
        #usersave = {"Name": username, "Phoneno": phone, "Pothole location": location, "Date": date, "VideoFile": file.filename, "Comments": comments, "Severity":severity}
        #records.save(usersave)
    return redirect('/client')


@app.route('/admin')
def admin():
    currmonth = str(datetime.now().month)
    curryear = str(datetime.now().year)
    details = records.find()
    
    total = 0
    pending = 0
    approved = 0
    solved = 0
    
    sol = 0
    appr = 0
    pend = 0
    rej = 0
    
    for det in details:
        if(det['email'] != "potholeadmin@gmail.com"):
            date = det['date']
            d = date.split('-')
    
            if(d[0] == curryear and d[1]==currmonth):
                total+=1
                if(det['status'] == "approved"):
                    approved+=1
                if(det['status'] == "completed"):
                    solved+=1
                if(det['status'] == "pending"):
                    pending+=1
            if(det['status'] == "approved"):
                appr+=1
            if(det['status'] == "completed"):
                sol+=1
            if(det['status'] == "pending"):
                pend+=1
            if(det['status'] == "rejected"):
                rej+=1

        
    totalrep = sol+appr+pend+rej
    
    docs = records.find({'email': {"$ne" : "potholeadmin@gmail.com"}}).sort("_id", -1).limit(5)
    docus = records.find({'email': {"$ne" : "potholeadmin@gmail.com"}}).sort("_id", -1).limit(5)
    locs = []
    count = 0
    for doc in docus:
        loca = doc['pothole location']
        lo = loca.split(',')
        count += 1
        dic = {'district': lo[2], 'state': lo[3], 'country': lo[5], 'count': count}
        locs.append(dic.copy())
    for loci in locs:
        print(loci['district'])
    print(locs[0].items())
    return render_template('dashboard.html',total=total,pending=pending,approved=approved,solved=solved,sol=sol,appr=appr,pend=pend,rej=rej,totalrep=totalrep,docs=docs,locs=locs)

@app.route('/pending')
def pending():
    details = records.find({ "status": "pending" }) 
    return render_template('pendingreports.html',details=details)

@app.route('/dummy')
def dummy():
    details = records.find()

    return render_template('pendsamp.html',details=details)

@app.route('/approved')
def approved():
    details = records.find({ "status": "approved" }) 
    return render_template('approved.html',details=details)

@app.route('/change/<username>',methods=['POST','GET'])
def change(username):
    if request.method == "POST":
        if request.form['approve'] == 'approve':
            records.find_one_and_update({"_id": ObjectId(username)}, {"$set": {"status":"approved"}})
        if request.form['approve'] == 'reject':
            records.find_one_and_update({"_id": ObjectId(username)}, {"$set": {"status":"rejected"}})
    return redirect('/pending')      


@app.route('/alter/<useremail>', methods=['POST','GET'])      
def alter(useremail):
    if request.method == "POST":
        if request.form['complete'] == 'completed':
            records.find_one_and_update({"_id": ObjectId(useremail)}, {"$set": {"status":"completed"}})
    return redirect('/approved')

@app.route('/allreports')
def allreports():
    docs = records.find({'email': {"$ne" : "potholeadmin@gmail.com"}}).sort("_id", -1)
    return render_template('allreports.html',docs=docs)

@app.route('/solved')
def solved():
    details = records.find({ "status": "completed" }) 
    return render_template('solved.html',details=details)


@app.route('/client')
def client():
    sol = 0
    appr = 0
    pend = 0
    rej = 0
    if "email" in session:
        email = session["email"]
        recs = records.find()
        docs = userrecords.find({ "email": email })
        for doc in docs:
            name = doc['name']
        for rec in recs:
            if(rec['email'] == email):
                
                if(rec['status'] == "completed"):
                    sol+=1
                if(rec['status'] == "pending"):
                    pend+=1
                if(rec['status'] == "rejected"):
                    rej+=1
                if(rec['status'] == "approved"):
                    appr+=1
            
    tot = sol+appr+pend+rej
    
    docs = records.find({"email": email})
    return render_template('client.html',sol=sol,rej=rej,pend=pend,appr=appr,tot=tot,docs=docs,name=name)

@app.route('/myreports')
def myreports():
    if "email" in session:
        email = session["email"]
        dets = records.find({"email": email})
        print(dets)
    return render_template('myreports.html',dets=dets)

@app.route('/file/<filename>')  
def file(filename):
    return mongo.send_file(filename)
    
@app.route('/logout', methods=['POST','GET'])
def logout():
    if "email" in session:
        session.pop("email",None)
    return redirect('/')


@app.route('/path',methods=['GET', 'POST'])
def path():
    global lat 
    lat = request.form.get('lati')
    global lon 
    lon = request.form.get('longi')
    latitude = str(lat)
    longitude = str(lon)
    geolocator = Nominatim(user_agent="geoapiExercises")
    global loc
    location = geolocator.geocode(latitude+","+longitude, timeout=None)
    print(location.address)
    loc = location.address
    return "hi"
    
    
if __name__=="__main__":
    app.run()