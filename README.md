# berryCADE
![](images/logo.jpg?raw=true)

## Introduction
An ANPR system running on a Raspberry Pi 3. It is able to detect the license plate's position in the image and extract the license plate text through Tesseract OCR. Validation result with database hosted on Heroku will control the GPIO outputs.

## How it works
1) PIR sensor detects motion
2) Pi Camera captures image with car plate
3) Image processing
4) Tesseract OCR
5) Validation with database

## LED indication
- Yellow (pin 10): Motion detected
- Red (pin 16): Access denied
- Green (pin 18): Access Granted

## Hardwares required:
- Raspberry Pi 3 Model B+ (or better)
- Pi Camera
- HC-SR501 PIR sensor
- Some LEDs, resistors and basic electrical components

## Setup
![](images/setup.jpg?raw=true)

## Files
- run.py: Main file
- createtable.py, insert.py: DB files
