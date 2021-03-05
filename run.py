import cv2
import imutils
import numpy as np
import pytesseract
from PIL import Image
from picamera.array import PiRGBArray
from picamera import PiCamera
import RPi.GPIO as GPIO
import psycopg2
import re
import time

#initialize rpi gpio
GPIO.setmode(GPIO.BOARD) #Set GPIO to pin numbering
pir = 8
yellow = 10
red = 16
green = 18
GPIO.setup(pir, GPIO.IN)
GPIO.setup(yellow, GPIO.OUT)
GPIO.setup(red, GPIO.OUT)
GPIO.setup(green, GPIO.OUT)
print ("Sensor initializing . . .")
time.sleep(5) #Give sensor time to startup
print ("Active")
print ("Press Ctrl+c to end program")

#initialize camera settings
camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 30
time.sleep(2) #time to setup

#heroku postgres db credential
DATABASE_URL = "postgres://xgcdthkexgrmxk:94093c3e42997d172ec998ffd9be108f9c9f3d569c854711045b1793dba5c3fd@ec2-54-87-34-201.compute-1.amazonaws.com:5432/d2mptevqotb4f1"

#image preprocessing functions 
def getContours(image):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) #convert to grayscale
    image_gray = cv2.bilateralFilter(image, 11, 17, 17) #blur image to reduce noise
    image_edged = cv2.Canny(image_gray, 30, 200) #get edges with canny
    cnts = cv2.findContours(image_edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:10] #sort contours from big to small
    return cnts, image_gray, image_edged

def maskImage(image_gray, image, screenCnt):
    mask = np.zeros(image_gray.shape, np.uint8)
    new_image = cv2.drawContours(mask, [screenCnt], 0, 255, -1)
    new_image = cv2.bitwise_and(image, image, mask=mask)
    return new_image, mask

def crop(image_gray, mask):
    (x, y) = np.where(mask==255)
    (topx, topy) = (np.min(x), np.min(y))
    (bottomx, bottomy) = (np.max(x), np.max(y))
    cropped = image_gray[topx:bottomx+1, topy:bottomy+1]
    return cropped

#database function to check car plates
def checkDB(plate_no):
    con = None
    sql = f"SELECT * FROM access WHERE plate_no = '{plate_no}'"
    try:
        con = psycopg2.connect(DATABASE_URL, sslmode="require")
        cur = con.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        print(rows)
        cur.close()
        
        if len(rows):
            result = True
        else:
            result = False
        
    except Exception as error:
        print("Database error")
        print(f"Cause: {error}")
        result = False
    
    finally:
        if con is not None:
            con.commit()
            con.close()
            return result

#main loop
try:
    while True:
        GPIO.output(red, False)
        GPIO.output(green, False)
        
        if GPIO.input(pir) == True: #If PIR pin goes high, motion is detected
            print ("Motion Detected!")
            GPIO.output(yellow, True)
            time.sleep(0.05)
            
            image = np.empty((640*480*3), dtype=np.uint8) #initialize captured image
            camera.capture(image, "bgr") #capture image, store into image
            image = image.reshape((480, 640, 3)) #reshape to image format
            cv2.imshow("captured image", image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            cnts, image_gray, image_edged = getContours(image)
            
            screenCnt = []
            for c in cnts:
                peri = cv2.arcLength(c, True) #get perimeter
                approx = cv2.approxPolyDP(c, 0.018*peri, True) #approximate no of sides
                if len(approx) == 4:
                    screenCnt = approx
                    break
            
            #print(screenCnt)
            if screenCnt!=[]:
                print("Car plate detected")
                new_image, mask = maskImage(image_gray, image, screenCnt) #new_image just for illustration
                cv2.imshow("detected image", new_image)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
                cropped = crop(image_gray, mask) #cropped license plate image
                _, cropped = cv2.threshold(cropped, 128, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
                cv2.imshow("cropped", cropped)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            
                plate_no = pytesseract.image_to_string(cropped, config="--psm 7")
                plate_no = re.sub("\W+", "", plate_no).upper() #delete non-alphanumeric including whitespace
                print(f"License Plate No: {plate_no}")
                
                if checkDB(plate_no):
                    print(f"Welcome {plate_no}")
                    GPIO.output(green, True)
                    time.sleep(8) #8 second window for car to enter
                    
                else:
                    print("Access denied")
                    GPIO.output(red, True)
                    time.sleep(5)
            
        elif GPIO.input(pir) == False:
            print("No motion detected")
            GPIO.output(yellow, False)
            time.sleep(0.05)

except:
    camera.close()
    GPIO.output(yellow, False)
    GPIO.output(red, False)
    GPIO.output(green, False)
    GPIO.cleanup()
    print("Camera closed")