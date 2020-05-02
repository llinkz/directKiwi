#!/bin/sh
python -m pip install --upgrade pip
python -m pip install numpy pillow future requests sounddevice samplerate matplotlib
echo -e "The setup is now finished.\nTo start the software from console, type ./directKiwi.py"
sleep 5