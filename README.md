# directKiwi v5.00

This piece of software is JUST a GUI written for Python 2.7 designed to fast connect audio socket to KiwiSDR servers around the world using modified versions @ https://github.com/dev-zzo/kiwiclient or related fork @ https://github.com/jks-prv/kiwiclient

Thanks to Pierre Ynard (linkfanel) for the listing of available KiwiSDR nodes used as source for the TDoA map update process (http://rx.linkfanel.net)

Thanks to Marco Cogoni (IS0KYB) for allowing me the use of his SNR measurements of the KiwiSDR network (http://sibamanna.duckdns.org/sdr_map.html)

##### Important _V5.00 update note_:
- If you already have a personalized directKiwi.cfg file, make a backup, upgrade and copy it later in directKiwi directory, it will be converted to work with version 5.00 automaticaly at first run
- Else, just rename directKiwi.sample.cfg to directKiwi.cfg`


## Stuff required to run the software:

* Tk
* python2-numpy
* python2-scipy
* python2-pygame
* python2-requests
* python2-pillow

## INSTALL AND RUN (on LINUX) Thanks Daniel E. for the install procedure

Install python 2.7

Install python-pip (search for the right package for your distro)

`git clone --recursive https://github.com/llinkz/directKiwi`

`cd directKiwi`

`./setup.sh` (this script will install python modules, it may fail, if so, install modules manually using your package manager)

`./directKiwi.py` (note: check the shebang if it fails on your system. On my Archlinux it should be "#!/usr/bin/python2" for example)


## INSTALL AND RUN (on MAC OS) Thanks Nicolas M. for the install procedure

* REQUIREMENT 	Xcode + Homebrew (https://brew.sh/index_fr)

Install Homebrew, in terminal : `/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"`

Install Python 2.7, in terminal : `brew install python@2`

`git clone --recursive https://github.com/llinkz/directKiwi`

`cd directKiwi`

`./setup.sh`  (this script will install python modules, it may fail, if so, install modules manually using your package manager)

`./directKiwi.py`


## LICENSE
* This python GUI code has been written and released under the "do what the f$ck you want with it" license


## WARNING
* This code may contain some silly procedures and dumb algorithms as I'm not a python guru, but it almost works so...
* This code is not optimized at all as well, will try to do my best during free time...

## TODO LIST
* enable IQ mode with direct recording to file ?

## CHANGE LOG 

* v5.00 : code clean up + cfg file now in json format + faster way to switch between nodes (left click only) - no more s-meter - icon size change possible
* v4.00 : the GUI is now using directTDoA design, nodes are displayed on a World map instead of a table
* v3.63 : fixed an issue with the India located remote that has few informations in kiwisdr.com/public listing page (source for updates)
* v3.62 : fixed a TK issue than was caused by python 2.7.15 version (code was written under 2.7.14
* v3.61 : agc/mgc listbox now (previously checkbox) + xxx.proxy.kiwisdr.com hosts (out of USA) locations fixed + autosorting list  at start
* v3.60 : adding default agc/mgc, mgc gain, hang, agc threshold, agc slope, agc decay to directKiwi.cfg configuration file
* v3.50 : adding default lowpass, highpass, modulation to directKiwi.cfg configuration file
* v3.40 : adding top bar menus for colors changing and saving directKiwi.cfg configuration (colors + geometry)
* v3.30 : host ports are checked before filling the node listing, normally all nodes listed are reachable now
* v3.20 : update process finally re-written and still using GeoIP - node listing now redrawing itself, no more restart needed
* v3.11 : some modifications in the console output log format + an update process bug has been solved
* v3.10 : adding labels, node listing and console scrollbars, cancel connect possibility + all CRLF converted to LF
* v3.00 : GUI based on TK now, no more PyQT stuff needed
* v2.30 : it's now possible to switch from node to node directly by double-clicking on the listing lines (prev forgiven)
* v2.20 : spectrum & recording modules has been removed, too many issues with client-side sound card settings
* v2.10 : adding the AGC control (manual or auto)
* v2.01 : KiwiSDRclient.py cleaned + S-meter bars removed
* v2.00 : BUG SOLVED: "QScrollbar & TextEdit refresh still not working with direct program lunch"
* v1.42 : adding some regexp checks to validate frequencies and IP:PORT/HOSTNAME:PORT in both top inputboxes
* v1.41 : adding the possibility to manually enter IP:PORT/HOSTNAME:PORT to connect to a specific KiwiSDR server
* v1.40 : most "update proc" bugs has been removed (major concerns wrong user entries in their kiwisdr setup/reg)
* v1.40beta : The KiwiSDR manual server listing update has been added - note: requires pygeoip module, still some bugs
* v1.33 : AM modulation has fixed BW (10kHz) - CW has frequency offset -1kHz BW set to 200Hz centered on desired freq
* v1.32 : changed LP & HP from QSlider to QScrollBar style for 100Hz steps clicks + some comments added + code clean-up
* v1.31 : dealing with processes & sub-processes + code clean-up
* v1.30 : adding the recorder extension
* v1.20 : adding the spectrum extension
* v1.10 : design modification + console output
* v1.1beta : adding the smeter
* v1.00 : first working version, basic, only freq/mode/bw, connect/disconnect


Enjoy

linkz

June 2019 update
