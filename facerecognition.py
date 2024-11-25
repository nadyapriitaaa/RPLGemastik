import cv2
import os
import time
from flask import *
from sklearn.neighbors import KNeighborsClassifier
import numpy as np
import mysql.connector
from deepface import DeepFace
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
import base64
import re


face_cascade = cv2.CascadeClassifier('resource/haarcascade_frontalface_default.xml')
facedir = 'static/faces'
list_hadir = []
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
frame = None


def dbconnection():
    conn = mysql.connector.connect(
            host = 'localhost',
            user = 'root',
            database = 'napritdb',
            password = ''
        )
    return conn

@socketio.on('frame')
def handle_event(data):
    global frame
    # Decode base64 image
    image_data = re.sub('^data:image/.+;base64,', '', data)
    image_bytes = base64.b64decode(image_data)
    np_array = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

if not os.path.isdir('static/faces'):
    os.makedirs('static/faces')

def get_atendance():
    list_hadir = []
    nama_hadir = []
    conn = dbconnection()
    myconn=conn.cursor()
    query = f"SELECT k.id_peserta, p.nama FROM kehadiran AS k JOIN peserta AS p ON k.id_peserta = p.id_peserta WHERE k.tanggal_kehadiran = '{datetime.now().strftime('%Y-%m-%d')}'"
    myconn.execute(query)
    result = myconn.fetchall()
    for i in result:
        list_hadir.append(i[0])
        nama_hadir.append(i[1])
    return list_hadir,nama_hadir

def updateHadirInfo():
    list_hadir, nama_hadir = get_atendance()
    socketio.emit('update_attendance', nama_hadir)

def get_registered_faceID():
    conn = dbconnection()
    myconn=conn.cursor()
    query = f"SELECT nama, id_peserta FROM peserta WHERE id_event = '{session['event_id']}' AND face_id_status = '1'"
    myconn.execute(query)
    result = myconn.fetchall()

    names = [row[0] for row in result]
    ids = [row[1] for row in result]
    return names, ids

def add_attendance(id):
    conn = dbconnection()
    myconn = conn.cursor()
    query = "INSERT INTO kehadiran(id_peserta, tanggal_kehadiran, waktu) VALUES (%s,%s,%s)"
    values = (id, datetime.now().strftime("%Y-%m-%d"),datetime.now().strftime("%H:%M:%S"))
    myconn.execute(query, values)
    conn.commit()

def getname(id):
    conn = dbconnection()
    myconn=conn.cursor()
    query = f"SELECT nama FROM peserta WHERE id_event = '{session['event_id']}' AND id_peserta = '{id}'"
    myconn.execute(query)
    result = myconn.fetchone()
    nama = result[0]
    return nama

def extract_faces(img):
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_points = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(20, 20))
        return face_points
    except:
        return []

def tambah(id, nama):
    global frame
    userid = str(id)
    userimagefolder = 'static/faces/' + userid + "_" + nama
    i = 1

    face_count = 0
    start_time = time.time()
    while True:
        # success, frame = camera.read()
        # if not success:
        #     break
        
        res = DeepFace.find(frame, db_path="static/faces/", enforce_detection=False, model_name="Facenet512")
        if len(res[0]['identity'])>0 and i == 1:
            socketio.emit('selesai')
        else:        
            conn = dbconnection()
            myconn = conn.cursor()
            query = f"UPDATE `peserta` SET `face_id_status` = '1' WHERE `peserta`.`id_peserta` = {userid}"
            myconn.execute(query)
            conn.commit()
            if not os.path.isdir(userimagefolder):
                os.makedirs(userimagefolder)   
            i=10
            faces = extract_faces(frame)
            if len(faces) == 1:  # Ensure only one face is detected
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

                    face_img = frame[y:y + h, x:x + w]
                    if face_count % 2 == 0:
                        cv2.imwrite(os.path.join(userimagefolder, f'{face_count}.jpg'), face_img)
                        print(face_count)
                    face_count += 1
                    if face_count == 50:
                        DeepFace.find(frame, db_path="static/faces/", enforce_detection=False, model_name="Facenet512")
                        # camera.release()
                        socketio.emit('selesai')
                        return

        # Display the frame
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
list_hadir, nama_hadir = get_atendance()
def cek():
    global list_hadir, nama_hadir, frame
    verif = 0
    detectedFace = None
    # camera = cv2.VideoCapture(0)
    skip_initial_frame = True  # Flag to skip the initial frame
    
    while True:
        updateHadirInfo()
        # state, frame = camera.read()

        # if state != True:
        #     break
        if skip_initial_frame:
            skip_initial_frame = False
            continue  # Skip the first frame

        res = DeepFace.find(frame, db_path="static/faces/", enforce_detection=False, model_name="Facenet512")
        if len(res[0]['identity'])>0:
            name = res[0]['identity'][0].split('/')[2].split("\\")[0].split("_")[1]
            id = res[0]['identity'][0].split('/')[2].split("\\")[0].split("_")[0]
            xmin = int(res[0]['source_x'][0])
            ymin = int(res[0]['source_y'][0])

            w = res[0]['source_w'][0]
            h = res[0]['source_h'][0]
            
            xmax = int(xmin+w)
            ymax = int(ymin+h)

            cv2.rectangle(frame, (xmin,ymin), (xmax,ymax), (0,255,0),1)
            cv2.rectangle(frame, (xmin,ymin), (xmax,ymin-20), (0,255,255),-1)
            cv2.putText(frame, name, (xmin,ymin), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 1, cv2.LINE_AA)
            
            if detectedFace == id:
                verif+=1
            else:
                detectedFace = id
                verif=0
            
            if id not in list_hadir:
                add_attendance(id)
                list_hadir.append(id)
                verif = 0
        else:
            verif = 0
            faces = extract_faces(frame)
            if len(faces) == 1:
                name = "unknown"
                xmin,ymin,w,h = faces[0]
                xmax = int(xmin+w)
                ymax = int(ymin+h)
                cv2.rectangle(frame, (xmin,ymin), (xmax,ymax), (0,255,0),1)
                cv2.rectangle(frame, (xmin,ymin), (xmax,ymin-20), (0,255,255),-1)
                cv2.putText(frame, name, (xmin,ymin), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 1, cv2.LINE_AA)
        
        if cv2.waitKey(1) == ord('q'):
            break
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_byte = buffer.tobytes()
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_byte + b'\r\n')
    # camera.release()