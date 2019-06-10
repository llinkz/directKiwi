#!/usr/bin/python
# -*- coding: utf-8 -*-
""" DirectKiwi python code. """

import codecs
import json
import os
import signal
import subprocess
from subprocess import PIPE
import sys
import threading
import time
import tkFileDialog
import tkMessageBox
import ttk
import unicodedata
import webbrowser
import re

from Tkinter import Tk, Label, Button, Entry, Text, Menu, Scale
from Tkinter import Scrollbar, Frame, Message, Canvas, CURRENT, NORMAL
from collections import OrderedDict
from shutil import copyfile
from tkColorChooser import askcolor

from PIL import Image, ImageTk

import requests


VERSION = "directKiwi v5.00"


class CheckUpdate(threading.Thread):
    """ Check if the sources are up before running the RunUpdate process """
    def __init__(self, parent=None):
        super(CheckUpdate, self).__init__()
        self.parent = parent

    def run(self):
        chk_linkf = chk_marco = 0
        APP.window2.writelog("Map Update process started ... Now checking if website sources are up, wait a moment ...")
        try:
            requests.get("http://rx.linkfanel.net/kiwisdr_com.js", timeout=2)
            chk_linkf = 1
        except requests.ConnectionError:
            APP.window2.writelog("Pierre's website is not reachable. Node listing update is not possible, try later.")
            APP.window2.update_button.configure(state="normal")
        try:
            requests.get("http://sibamanna.duckdns.org/snrmap_4bands.json", timeout=2)
            chk_marco = 1
        except requests.ConnectionError:
            APP.window2.writelog("Marco's website is not reachable. Node listing update is not possible, try later.")
            APP.window2.update_button.configure(state="normal")
        if chk_linkf == 1 and chk_marco == 1:
            APP.window2.writelog("OK looks good, map update in progress...please wait until software restart..")
            RunUpdate().run()


class RunUpdate(threading.Thread):
    """ Update map process """
    def __init__(self, parent=None):
        super(RunUpdate, self).__init__()
        self.parent = parent

    def run(self):
        try:
            # Get the full KiwiSDR node list from linkfanel website
            nodelist = requests.get("http://rx.linkfanel.net/kiwisdr_com.js")
            # Convert that listing to fit a JSON formatting (also removind bad/incomplete node entries)
            kiwilist = re.sub(r"{\n(.*?),\n(.*?),\n\t\},", "", re.sub(r"},\n]\n;", "\t}\n]", re.sub(
                r"(//.+\n){4}\n.+", "", nodelist.text, 0), 0), 0)
            json_data = json.loads(kiwilist)
            # Get the full KiwiSDR SNR list from Marco's website
            snrlist = requests.get("http://sibamanna.duckdns.org/snrmap_4bands.json")
            json_data2 = json.loads(snrlist.text)
            # Remove the existing node database
            if os.path.isfile('directKiwi_server_list.db'):
                os.remove('directKiwi_server_list.db')
            # Open a new database
            with codecs.open('directKiwi_server_list.db', 'w', encoding='utf8') as db_file:
                db_file.write("[\n")
                # Parse linkfanel listing, line per line
                for i in range(len(json_data)):
                    # Adding a display in the console window, to be sure something happens (displaying . for each node)
                    APP.window2.console_window.insert('end -1 lines', ".")
                    APP.window2.console_window.see('end')
                    # Check if node has an entry in Marco SNR database
                    for index, element in enumerate(json_data2['features']):
                        if json_data[i]['id'] in json.dumps(json_data2['features'][index]):
                            if json_data[i]['tdoa_id'] == '':
                                node_id = json_data[i]['url'].split('//', 1)[1].split(':', 1)[0]
                                try:
                                    # Search for an IP in the hostname, becomes the node ID name if OK
                                    ipfield = re.search(r'\b((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
                                                        r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
                                                        r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
                                                        r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\b'
                                                        , json_data[i]['url'].split('//', 1)[1].split(':', 1)[0])
                                    node_id = str(ipfield.group(1))
                                except:
                                    pass
                                try:
                                    # Search for a Hamcall in the name, becomes the node ID name if OK
                                    hamcallfield = re.search(
                                        r"(.*)(\s|,|/|^)([A-Za-z]{1,2}[0-9][A-Za-z]{1,3})(\s|,|/|@|-)(.*)",
                                        json_data[i]['name'])
                                    node_id = hamcallfield.group(3).upper()
                                except:
                                    pass
                            else:
                                # Else we are using the TDoA field entry set by the KiwiSDR hosters
                                node_id = json_data[i]['tdoa_id']
                            try:
                                # Parse the geographical coordinates to place the node at the right place on World map
                                gpsfield = re.search(r'([-+]?[0-9]{1,2}(\.[0-9]*)?)(,| ) '
                                                     r'?([-+]?[0-9]{1,3}(\.[0-9]*))?', json_data[i]['gps'][1:-1])
                                nodelat = gpsfield.group(1)
                                nodelon = gpsfield.group(4)
                            except:
                                # For admins not respecting KiwiSDR admin page GPS field format (nn.nnnnnn, nn.nnnnnn)
                                # => nodes will be shown at World center, as it could make the update process fail
                                print "*** Error reading <gps> field : This node will be displayed at 0N 0E position >>"
                                nodelat = nodelon = "0"
                            # Now the lazy way to create a json-type line in kiwiSDR node listing, manually
                            db_file.write(' { \"mac\":\"' + json_data[i]['id'] + '\", \"url\":\"' + json_data[i]['ur\
l'].split('//', 1)[1] + '\", \"gps\":\"' + json_data[i]['fixes_min'] + '\", \"id\":\"' + node_id + '\", \"l\
at\":\"' + nodelat + '\", \"lon\":\"' + nodelon + '\", \"name\":\"' + unicodedata.normalize("NFKD", json_data[i]["n\
ame"]).encode("ascii", "ignore").replace("\"", "").replace(" ", "_").replace("!", "_") + '\", \"use\
rs\":\"' + json_data[i]['users'] + '\", \"usersmax\":\"' + json_data[i]['users_max'] + '\", \"snr\
1\":\"' + str(element['properties']['snr1_avg']) + '\", \"snr2\":\"' + str(element['properties']['snr2_avg']) + '\", \"\
snr3\":\"' + str(element['properties']['snr3_avg']) + '\", \"snr\
4\":\"' + str(element['properties']['snr4_avg']) + '\", \"nlvl1\":\"' + str(element['properties']['bg1_avg']) + '\", \"\
nlvl2\":\"' + str(element['properties']['bg2_avg']) + '\", \"nlvl\
3\":\"' + str(element['properties']['bg3_avg']) + '\", \"nlvl4\":\"' + str(element['properties']['bg4_avg']) + '\"},\n')
                        else:
                            pass
                # Here is the hardcode for my own KiwiSDR node, because it's not public
                db_file.write(' { "mac":"04a316df1bca", "url":"linkz.ddns.net:8073", "gps":"30", "id":"linkz", \
                "lat":"45.4", "lon":"5.3", "name":"directKiwi_GUI_developer,_French_Alps", "users":"0", \
                "usersmax":"4", "snr1":"0", "snr2":"0", "snr3":"0", "snr4":"0", "nlvl1":"0", "nlvl2":"0", \
                "nlvl3":"0", "nlvl4":"0"}\n]')
                db_file.close()
                # If update process finish normally, we can make a backup copy of the server listing
                copyfile("directKiwi_server_list.db", "directKiwi_server_list.db.bak")
                # Then we restart the GUI
                Restart().run()
        except Exception as update_Error:
            print "UPDATE FAIL, sorry => " + str(update_Error)


class ReadCfg(object):
    """ DirectKiwi configuration file read process. """
    def __init__(self):
        pass

    def __str__(self):
        return self.__class__.__name__

    @staticmethod
    def read_cfg():
        """ DirectKiwi configuration file read process. """
        global CFG, DX0, DY0, DX1, DY1, DMAP, MAPFL, WHITELIST, BLACKLIST, STDCOLOR, FAVCOLOR, BLKCOLOR, ICONSIZE
        global LP_CUT, HP_CUT, AGC, HANG, MGAIN, THRESHOLD, SLOPE, DECAY
        try:
            # Read the config file v5.0 format and declare variables
            with open('directKiwi.cfg', 'r') as config_file:
                CFG = json.load(config_file, object_pairs_hook=OrderedDict)
            DX0, DX1, DY0, DY1 = CFG["map"]["x0"], CFG["map"]["x1"], CFG["map"]["y0"], CFG["map"]["y1"]
            DMAP, MAPFL, ICONSIZE = CFG["map"]["file"], CFG["map"]["mapfl"], CFG["map"]["iconsize"]
            STDCOLOR, FAVCOLOR, BLKCOLOR = CFG["map"]["std"], CFG["map"]["fav"], CFG["map"]["blk"]
            LP_CUT, HP_CUT, AGC = CFG["demod"]["lp_cut"], CFG["demod"]["hp_cut"], CFG["demod"]["agc"]
            HANG, MGAIN = CFG["demod"]["hang"], CFG["demod"]["mgain"]
            THRESHOLD, SLOPE, DECAY = CFG["demod"]["thres"], CFG["demod"]["slope"], CFG["demod"]["decay"]
            WHITELIST, BLACKLIST = CFG["nodes"]["whitelist"], CFG["nodes"]["blacklist"]
        except (ImportError, ValueError):
            # If an old config file format is detected, convert it to v5.0 format
            with open('directKiwi.cfg', "r") as old_config_file:
                configline = old_config_file.readlines()
                CFG = {'map': {}, 'demod': {}, 'nodes': {}}
                CFG["map"]["iconsize"] = 5
                CFG["map"]["x0"] = configline[3].split(',')[0]
                CFG["map"]["x1"] = configline[3].split(',')[2]
                CFG["map"]["y0"] = configline[3].split(',')[1]
                CFG["map"]["y1"] = configline[3].replace("\n", "").split(',')[3]
                CFG["map"]["file"] = configline[5].split('\n')[0]
                CFG["map"]["mapfl"] = int(configline[7].replace("\n", "")[0])
                CFG["map"]["std"] = configline[13].replace("\n", "").split(',')[0]
                CFG["map"]["fav"] = configline[13].replace("\n", "").split(',')[1]
                CFG["map"]["blk"] = configline[13].replace("\n", "").split(',')[2]
                CFG["demod"]["lp_cut"] = int(configline[15].split(',')[0])
                CFG["demod"]["hp_cut"] = int(configline[15].split(',')[1])
                CFG["demod"]["agc"] = int(configline[15].split(',')[2])
                CFG["demod"]["hang"] = int(configline[15].split(',')[3])
                CFG["demod"]["mgain"] = int(configline[15].split(',')[4])
                CFG["demod"]["thres"] = int(configline[15].split(',')[5])
                CFG["demod"]["slope"] = int(configline[15].split(',')[6])
                CFG["demod"]["decay"] = int(configline[15].split(',')[7])
                if configline[9] == "\n":
                    CFG["nodes"]["whitelist"] = []
                else:
                    CFG["nodes"]["whitelist"] = configline[9].replace("\n", "").split(',')
                if configline[11] == "\n":
                    CFG["nodes"]["blacklist"] = []
                else:
                    CFG["nodes"]["blacklist"] = configline[11].replace("\n", "").split(',')
                copyfile("directKiwi.cfg", "directKiwi.do-not-use-anymore.cfg")
            with open('directKiwi.cfg', 'w') as config_file:
                json.dump(OrderedDict(sorted(CFG.items(), key=lambda t: t[0])), config_file, indent=2)
            sys.exit("v4.00 configuration file format has been converted to v5.00 one.\nRestart the GUI now")


class SaveCfg(object):
    """ DirectKiwi configuration file save process. """
    def __init__(self):
        pass

    def __str__(self):
        return self.__class__.__name__

    @staticmethod
    def save_cfg(cat, field, input):
        """ always consider the map position as default and always save it, whatever parameter has been changed """
        CFG["map"]["x0"], CFG["map"]["y0"] = str(bbox_2[0]), str(bbox_2[1])
        CFG["map"]["x1"], CFG["map"]["y1"] = str(bbox_2[2]), str(bbox_2[3])
        # Sets the new parameter value to the right category
        CFG[cat][field] = input
        # Now save the config file
        with open('directKiwi.cfg', 'w') as config_file:
            json.dump(CFG, config_file, indent=2)


class StopListen(object):
    """ Process that kills the web socket to stop listening mode. """
    def __init__(self):
        pass

    @staticmethod
    def run():
        """ Process that kills the web socket to stop listening mode. """
        global LISTENMODE
        LISTENMODE = "0"
        APP.window2.writelog("Stopping Listen mode")
        APP.title(VERSION)
        APP.window2.stop_button.configure(state="disabled")
        try:
            os.kill(CLIENT_PID, signal.SIGTERM)
        except ImportError:
            pass


class StartKiwiSDRclient(threading.Thread):
    """ DirectKiwi Main audio socket process. """
    def __init__(self):
        super(StartKiwiSDRclient, self).__init__()

    def run(self):
        """ DirectKiwi Main audio socket process. """
        global CLIENT_PID, LISTENMODE
        try:
            #  '-g', '1', '50', '0', '-100', '6', '1000'  <==== static AGC settings
            #  1= AGC (on)  50=Manual Gain (dB) 0=Hang (off)  -100=Threshold (dB) 6=Slope (dB) 1000=Decay (ms)
            #  -L and -H are low & high pass demod filters settings
            socket_connect = subprocess.Popen(
                [sys.executable, 'KiwiSDRclient.py', '-s', HOST.rsplit("$", 14)[0].rsplit(":", 2)[0], '-p',
                 HOST.rsplit("$", 14)[0].rsplit(":", 2)[1], '-f', FREQUENCY, '-m', MODE, '-L', str(LP_CUT),
                 '-H', str(HP_CUT), '-g', str(AGC), str(MGAIN), str(HANG), str(THRESHOLD), str(SLOPE),
                 str(DECAY)], stdout=PIPE, shell=False)
            CLIENT_PID = socket_connect.pid
            LISTENMODE = "1"
            APP.window2.stop_button.configure(state="normal")
        except ValueError:
            print "error: unable to demodulate this node"
            LISTENMODE = "0"


class FillMapWithNodes(object):
    """ DirectKiwi process to display the nodes on the World Map. """
    def __init__(self, parent):
        self.parent = parent

    def run(self):
        """ DirectKiwi process to display the nodes on the World Map. """
        global NODE_COUNT
        # Open the nodelist db
        with open('directKiwi_server_list.db') as node_db:
            db_data = json.load(node_db)
            NODE_COUNT = len(db_data)
            for node_index in range(NODE_COUNT):
                # For each node calculate the average SNR for the whole HF band
                temp_snr_avg = (int(db_data[node_index]["snr1"]) + int(db_data[node_index]["snr2"]) + int(
                    db_data[node_index]["snr3"]) + int(db_data[node_index]["snr4"])) / 4
                # Change the icon color of favorites, blacklist and standards nodes and apply a gradiant // SNR
                if db_data[node_index]["mac"] in WHITELIST:
                    node_color = (self.color_variant(FAVCOLOR, (int(temp_snr_avg) - 45) * 5))
                elif db_data[node_index]["mac"] in BLACKLIST:
                    node_color = (self.color_variant(BLKCOLOR, (int(temp_snr_avg) - 45) * 5))
                else:
                    node_color = (self.color_variant(STDCOLOR, (int(temp_snr_avg) - 45) * 5))
                # Apply the map filtering
                if MAPFL == 1 and db_data[node_index]["mac"] not in BLACKLIST:
                    self.add_point(node_index, node_color, db_data)
                elif MAPFL == 2 and db_data[node_index]["mac"] in WHITELIST:
                    self.add_point(node_index, node_color, db_data)
                elif MAPFL == 3 and db_data[node_index]["mac"] in BLACKLIST:
                    self.add_point(node_index, node_color, db_data)
                elif MAPFL == 0:
                    self.add_point(node_index, node_color, db_data)
        self.parent.canvas.scan_dragto(-int(DX0.split('.')[0]), -int(DY0.split('.')[0]), gain=1)  # adjust map pos.
        self.parent.show_image()

    def add_point(self, node_index, node_color, db_data):
        """ Process that add node icons over the World map. """
        mykeys = ['url', 'mac', 'id', 'name', 'users', 'usersmax', 'gps', 'snr1', 'snr2', 'snr3', 'snr4', 'nlvl1',
                  'nlvl2', 'nlvl3', 'nlvl4']
        node_lat = self.convert_lat(db_data[node_index]["lat"])
        node_lon = self.convert_lon(db_data[node_index]["lon"])
        node_tag = str('$'.join([db_data[node_index][x] for x in mykeys]))
        try:
            self.parent.canvas.create_rectangle(node_lon, node_lat, node_lon + float(ICONSIZE),
                                                node_lat + float(ICONSIZE), fill=node_color, tag=node_tag)
            self.parent.canvas.tag_bind(node_tag, "<Button-1>", self.parent.onclickleft)
            self.parent.canvas.tag_bind(node_tag, "<Button-3>", self.parent.onclickright)
        except NameError:
            print "OOPS - Error in adding the point to the map"

    @staticmethod
    def convert_lat(lat):
        """ Process that convert the real node latitude coordinates to adapt to GUI window map geometry. """
        if float(lat) > 0:  # nodes are between LATITUDE 0 and 90N
            return 987.5 - (float(lat) * 11)
        return 987.5 + (float(0 - float(lat)) * 11)

    @staticmethod
    def convert_lon(lon):
        """ Process that converts the real node longitude coordinates to adapt to GUI window map geometry. """
        return 1907.5 + ((float(lon) * 1910) / 180)

    @staticmethod
    def color_variant(hex_color, brightness_offset=1):
        """ Process that changes the brightness (only) of a specific RGB color
        source : https://chase-seibert.github.io/blog/2011/07/29/python-calculate-lighterdarker-rgb-colors.html. """
        rgb_hex = [hex_color[x:x + 2] for x in [1, 3, 5]]
        new_rgb_int = [int(hex_value, 16) + brightness_offset for hex_value in rgb_hex]
        new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int]
        return "#" + "".join(["0" + hex(i)[2:] if len(hex(i)[2:]) < 2 else hex(i)[2:] for i in new_rgb_int])


class ZoomAdvanced(Frame):
    """ Process that creates the GUI map canvas, enabling move & zoom on a picture. """
    def __init__(self, parent):
        # source: stackoverflow.com/questions/41656176/tkinter-canvas-zoom-move-pan?noredirect=1&lq=1
        Frame.__init__(self, parent=None)
        parent.geometry("1050x600+200+50")
        global LISTENMODE
        ReadCfg().read_cfg()
        LISTENMODE = "0"
        # self.x = self.y = 0
        # Create canvas and put image on it
        self.canvas = Canvas(self.master, highlightthickness=0)
        # self.sbarv = Scrollbar(self, orient=VERTICAL)
        # self.sbarh = Scrollbar(self, orient=HORIZONTAL)
        # self.sbarv.config(command=self.canvas.yview)
        # self.sbarh.config(command=self.canvas.xview)
        # self.canvas.config(yscrollcommand=self.sbarv.set)
        # self.canvas.config(xscrollcommand=self.sbarh.set)
        # self.sbarv.grid(row=0, column=1, stick=N + S)
        # self.sbarh.grid(row=1, column=0, sticky=E + W)
        self.canvas.grid(row=0, column=0, sticky='nswe')
        self.canvas.update()  # wait till canvas is created
        # Make the canvas expandable
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        # Bind events to the Canvas
        self.canvas.bind('<Configure>', self.show_image)  # canvas is resized
        self.canvas.bind('<ButtonPress-1>', self.move_from)  # map move
        self.canvas.bind('<B1-Motion>', self.move_to)  # map move
        # self.canvas.bind_all('<MouseWheel>', self.wheel)  # Windows Zoom disabled in this version !
        # self.canvas.bind('<Button-5>', self.wheel)  # Linux Zoom disabled in this version !
        # self.canvas.bind('<Button-4>', self.wheel)  # Linux Zoom disabled in this version !
        self.image = Image.open(DMAP)
        self.width, self.height = self.image.size
        self.imscale = 1.0  # scale for the image
        self.delta = 2.0  # zoom magnitude
        # Put image into container rectangle and use it to set proper coordinates to the image
        self.container = self.canvas.create_rectangle(0, 0, self.width, self.height, width=0)
        self.canvas.config(scrollregion=(0, 0, self.width, self.height))
        self.start_x = None
        self.start_y = None
        self.canvas.scan_dragto(-int(DX0.split('.')[0]), -int(DY0.split('.')[0]), gain=1)  # adjust map pos.
        self.show_image()
        time.sleep(0.2)
        FillMapWithNodes(self).run()

    def onclickleft(self, event=None):
        """ Left Mouse Click bind to start demodulation from the node. """
        global HOST, FREQUENCY, CLIENT_PID, LISTENMODE
        HOST = self.canvas.gettags(self.canvas.find_withtag(CURRENT))[0]
        FREQUENCY = APP.window2.entry1.get()
        permit_web = "no"
        if FREQUENCY == "" or float(FREQUENCY) < 5 or float(FREQUENCY) > 29995:
            APP.window2.writelog("Check FREQUENCY field !")
        else:
            try:  # check if the node is answering
                chktimeout = 1  # timeout of the node check
                checkthenode = requests.get("http://" + str(HOST).rsplit("$", 14)[0] + "/status", timeout=chktimeout)
                infonodes = checkthenode.text.split("\n")
                if len(infonodes) == 22 and "status" in infonodes[0]:
                    try:
                        if infonodes[6].rsplit("=", 2)[1] == infonodes[7].rsplit("=", 2)[1]:  # users Vs. users_max
                            APP.window2.writelog(" " + str(HOST).rsplit("$", 14)[0].rsplit(":", 2)[0] + " is full.")
                        elif infonodes[1].rsplit("=", 2)[1] == "yes":                         # offline=no/yes
                            APP.window2.writelog(" " + str(HOST).rsplit("$", 14)[0].rsplit(":", 2)[0] + " is offline.")
                        else:
                            permit_web = "yes"
                    except ValueError:
                        pass
                else:
                    APP.window2.writelog("Sorry " + str(HOST).rsplit("$", 14)[0].rsplit(":", 2)[0] + " is unreachable.")
            except requests.RequestException:
                APP.window2.writelog("Sorry " + str(HOST).rsplit("$", 14)[0].rsplit(":", 2)[0] + " has problems.")
            if permit_web == "yes":
                if LISTENMODE == "0":
                    StartKiwiSDRclient().start()
                else:
                    try:
                        os.kill(CLIENT_PID, signal.SIGTERM)
                        StartKiwiSDRclient().start()
                    except NameError:
                        pass
                APP.window2.writelog(" ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ")
                APP.window2.writelog(
                    "[ " + str(HOST).rsplit("$", 14)[0].rsplit(":", 2)[0] + " / " + FREQUENCY + " kHz / " + str(
                        MODE).upper() + " / " + str(HP_CUT - LP_CUT) + "Hz ]")
                APP.window2.writelog("[ " + str(HOST).rsplit("$", 14)[3].replace("_", " ") + " ]")
                APP.title(str(VERSION) + " - [ " + str(HOST).rsplit("$", 14)[0].rsplit(":", 2)[
                    0] + " / " + FREQUENCY + " kHz / " + str(MODE).upper() + " / " + str(HP_CUT - LP_CUT) + "Hz ]")

    def onclickright(self, event):
        """ Right Mouse Click bind to watch node SNR values / web browser / fav / blacklist. """
        global HOST, WHITELIST, BLACKLIST, LISTENMODE, FREQUENCY
        HOST = self.canvas.gettags(self.canvas.find_withtag(CURRENT))[0]
        menu = Menu(self, tearoff=0, fg="black", bg="grey", font='TkFixedFont 7')
        permit_web = "no"
        n_field = HOST.rsplit("$", 14)
        #  HOST.rsplit("$", 14)[#] <<
        #  0=HOST  1=id  2=short name  3=name  4=users  5=users max  6=GPS fix/min
        #  7=SNR 0-2 MHz  8=SNR 2-10 MHz  9=SNR 10-20 MHz  10=SNR 20-30 MHz
        #  11=Noise 0-2 MHz  12=Noise 2-10 MHz 13=Noise 10-20 MHz  14=Noise 20-30 MHz
        temp_snr_avg = (int(n_field[7]) + int(n_field[8]) + int(n_field[9]) + int(n_field[10])) / 4
        temp_noise_avg = (int(n_field[11]) + int(n_field[12]) + int(n_field[13]) + int(n_field[14])) / 4
        font_snr1 = font_snr2 = font_snr3 = font_snr4 = 'TkFixedFont 7'
        FREQUENCY = APP.window2.entry1.get()
        try:  # check if the node is answering
            chktimeout = 1  # timeout of the node check
            checkthenode = requests.get("http://" + n_field[0] + "/status", timeout=chktimeout)
            infonodes = checkthenode.text.split("\n")
            try:  # node filtering
                permit_web = "no"
                if infonodes[6].rsplit("=", 2)[1] == infonodes[7].rsplit("=", 2)[1]:  # users Vs. users_max
                    menu.add_command(label=n_field[2] + " node have no available slots",
                                     background=(self.color_variant("#FF0000", (int(temp_snr_avg) - 50) * 5)),
                                     foreground=self.get_font_color(
                                         (self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                                     command=None)
                elif infonodes[1].rsplit("=", 2)[1] == "yes":  # offline=no/yes
                    menu.add_command(label=n_field[2] + " node is currently offline",
                                     background=(self.color_variant("#FF0000", (int(temp_snr_avg) - 50) * 5)),
                                     foreground=self.get_font_color(
                                         (self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                                     command=None)
                else:  # all ok for this node
                    permit_web = "yes"
            except IndexError:
                if "not found" in infonodes[13]:
                    menu.add_command(
                        label=n_field[2] + " node is not available. (proxy.kiwisdr.com error)",
                        background=(self.color_variant("#FF0000", (int(temp_snr_avg) - 50) * 5)),
                        foreground=self.get_font_color((self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                        command=None)
                    permit_web = "no"

        except requests.RequestException as req_error:
            menu.add_command(
                label=n_field[2] + " node is not available. " + str(req_error.message).rsplit('(')[2],
                background=(self.color_variant("#FF0000", (int(temp_snr_avg) - 50) * 5)),
                foreground=self.get_font_color(
                    (self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))), command=None)
            permit_web = "no"

        if permit_web == "yes" and FREQUENCY != "" and 5 < float(FREQUENCY) < 30000:
            try:
                menu.add_command(
                    label="Open \"" + n_field[0] + "/f=" + str(FREQUENCY) + str(
                        MODE).lower() + "z8\" in browser",
                    state=NORMAL, background=(self.color_variant(STDCOLOR, (int(temp_snr_avg) - 50) * 5)),
                    foreground=self.get_font_color((self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                    command=self.openinbrowser)
                if float(FREQUENCY) <= 2000:
                    font_snr1 = 'TkFixedFont 8 bold'
                elif 2001 < float(FREQUENCY) <= 10000:
                    font_snr2 = 'TkFixedFont 8 bold'
                elif 10001 < float(FREQUENCY) <= 20000:
                    font_snr3 = 'TkFixedFont 8 bold'
                elif 20001 < float(FREQUENCY) <= 30000:
                    font_snr4 = 'TkFixedFont 8 bold'
            except ImportError:
                pass
        menu.add_command(
            label=n_field[2] + " | " + n_field[3].replace("_", " ") + " | USERS " + n_field[4] + "/" + n_field[
                5] + " | GPS " + n_field[6] + " fix/min", state=NORMAL,
            background=(self.color_variant(STDCOLOR, (int(temp_snr_avg) - 50) * 5)),
            foreground=self.get_font_color((self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))), command=None)
        try:
            if n_field[11] != '0':
                menu.add_separator()
                menu.add_command(label="AVG SNR on 0-30 MHz: " + str(temp_snr_avg) + " dB - AVG Noise: " + str(
                    temp_noise_avg) + " dBm (S" + str(self.convert_dbm_to_smeter(int(temp_noise_avg))) + ")",
                                 background=(self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5)),
                                 foreground=self.get_font_color(
                                     (self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))), command=None)
                menu.add_separator()
                menu.add_command(
                    label="AVG SNR on 0-2 MHz: " + n_field[7] + " dB - AVG Noise: " + n_field[
                        11] + " dBm (S" + str(self.convert_dbm_to_smeter(int(n_field[11]))) + ")",
                    background=(self.color_variant("#FFFF00", (int(n_field[7]) - 50) * 5)),
                    foreground=self.get_font_color(
                        (self.color_variant("#FFFF00", (int(n_field[7]) - 50) * 5))), font=font_snr1,
                    command=None)
                menu.add_command(label="AVG SNR on 2-10 MHz: " + n_field[8] + " dB - AVG Noise: " +
                                       n_field[12] + " dBm (S" + str(
                    self.convert_dbm_to_smeter(int(n_field[12]))) + ")", background=(
                    self.color_variant("#FFFF00", (int(n_field[8]) - 50) * 5)),
                                 foreground=self.get_font_color(
                                     (self.color_variant("#FFFF00", (int(n_field[8]) - 50) * 5))),
                                 font=font_snr2, command=None)
                menu.add_command(
                    label="AVG SNR on 10-20 MHz: " + n_field[9] + " dB - AVG Noise: " +
                          n_field[
                              13] + " dBm (S" + str(self.convert_dbm_to_smeter(int(n_field[13]))) + ")",
                    background=(self.color_variant("#FFFF00", (int(n_field[9]) - 50) * 5)),
                    foreground=self.get_font_color(
                        (self.color_variant("#FFFF00", (int(n_field[9]) - 50) * 5))), font=font_snr3,
                    command=None)
                menu.add_command(label="AVG SNR on 20-30 MHz: " + n_field[10] + " dB - AVG Noise: " +
                                       n_field[14] + " dBm (S" + str(
                    self.convert_dbm_to_smeter(int(n_field[14]))) + ")", background=(
                    self.color_variant("#FFFF00", (int(n_field[10]) - 50) * 5)),
                                 foreground=self.get_font_color(
                                     (self.color_variant("#FFFF00", (int(n_field[10]) - 50) * 5))),
                                 font=font_snr4, command=None)
            else:
                menu.add_separator()
        except ImportError:
            pass
        if n_field[1] in WHITELIST:  # if node is a favorite
            menu.add_command(label="remove from favorites", command=self.remfavorite)
        elif n_field[1] not in BLACKLIST:
            menu.add_command(label="add to favorites", command=self.addfavorite)
        if n_field[1] in BLACKLIST:  # if node is blacklisted
            menu.add_command(label="remove from blacklist", command=self.remblacklist)
        elif n_field[1] not in WHITELIST:
            menu.add_command(label="add to blacklist", command=self.addblacklist)
        menu.post(event.x_root, event.y_root)  # popup placement

    @staticmethod
    def get_font_color(original_color):
        """ Adapting the font color regarding background luminosity. """
        # src stackoverflow.com/questions/946544/good-text-foreground-color-for-a-given-background-color/946734#946734
        rgb_hex = [original_color[x:x + 2] for x in [1, 3, 5]]
        if int(rgb_hex[0], 16) * 0.299 + int(rgb_hex[1], 16) * 0.587 + int(rgb_hex[2], 16) * 0.114 > 186:
            return "#000000"
        return "#FFFFFF"
        # if (red*0.299 + green*0.587 + blue*0.114) > 186 use #000000 else use #ffffff

    @staticmethod
    def convert_dbm_to_smeter(dbm):
        """ Routine that converts dbm values to S-meter unit (for node submenus SNR display). """
        dbm_values = [-121, -115, -109, -103, -97, -91, -85, -79, -73, -63, -53, -43, -33, -23, -13, -3]
        if dbm != 0:
            return next(x[0] for x in enumerate(dbm_values) if x[1] > dbm)
        return "--"

    @staticmethod
    def color_variant(hex_color, brightness_offset=1):
        """ Routine used to change color brightness according to SNR scaled value. """
        # source: https://chase-seibert.github.io/blog/2011/07/29/python-calculate-lighterdarker-rgb-colors.html
        rgb_hex = [hex_color[x:x + 2] for x in [1, 3, 5]]
        new_rgb_int = [int(hex_value, 16) + brightness_offset for hex_value in rgb_hex]
        new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int]
        return "#" + "".join(["0" + hex(i)[2:] if len(hex(i)[2:]) < 2 else hex(i)[2:] for i in new_rgb_int])

    @staticmethod
    def addfavorite():
        """ Add Favorite node submenu entry. """
        WHITELIST.append(HOST.rsplit("$", 14)[1])
        SaveCfg().save_cfg("nodes", "whitelist", WHITELIST)
        Restart().run()

    @staticmethod
    def remfavorite():
        """ Remove Favorite node submenu entry. """
        WHITELIST.remove(HOST.rsplit("$", 14)[1])
        SaveCfg().save_cfg("nodes", "whitelist", WHITELIST)
        Restart().run()

    @staticmethod
    def addblacklist():
        """ Add Blacklist node submenu entry. """
        BLACKLIST.append(HOST.rsplit("$", 14)[1])
        SaveCfg().save_cfg("nodes", "blacklist", BLACKLIST)
        Restart().run()

    @staticmethod
    def remblacklist():
        """ Remove Blacklist node submenu entry. """
        BLACKLIST.remove(HOST.rsplit("$", 14)[1])
        SaveCfg().save_cfg("nodes", "blacklist", BLACKLIST)
        Restart().run()

    @staticmethod
    def openinbrowser():
        """ Browser call with selected FREQUENCY to node (fixed zoom level at 8). """
        if FREQUENCY != 10000:
            url = "http://" + str(HOST).rsplit("$", 14)[0] + "/?f=" + str(FREQUENCY) + str(MODE).lower() + "z8"
        else:
            url = "http://" + str(HOST).rsplit("$", 14)[0]
        webbrowser.open_new(url)

    def scroll_y(self, *args):
        """ Scroll y. """
        self.canvas.yview(*args)  # scroll vertically
        self.show_image()  # redraw the image

    def scroll_x(self, *args):
        """ Scroll x. """
        self.canvas.xview(*args)  # scroll horizontally
        self.show_image()  # redraw the image

    def move_from(self, event):
        """ Move from. """
        self.canvas.scan_mark(event.x, event.y)

    def move_to(self, event):
        """ Move to. """
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.show_image()  # redraw the image

    def wheel(self, event):
        """ Routine for mouse wheel actions. """
        # global bbox
        x_wheel = self.canvas.canvasx(event.x)
        y_wheel = self.canvas.canvasy(event.y)
        bbox = self.canvas.bbox(self.container)  # get image area
        if bbox[0] < x_wheel < bbox[2] and bbox[1] < y_wheel < bbox[3]:
            pass  # Ok! Inside the image
        else:
            return  # zoom only inside image area
        scale = 1.0
        # Respond to Linux (event.num) or Windows (event.delta) wheel event
        if event.num == 5 or event.delta == -120:  # scroll down
            i = min(self.width, self.height)
            if int(i * self.imscale) < 2000:
                return  # block zoom if image is less than 600 pixels
            self.imscale /= self.delta
            scale /= self.delta
        if event.num == 4 or event.delta == 120:  # scroll up
            i = min(self.canvas.winfo_width(), self.canvas.winfo_height())
            if i < self.imscale:
                return  # 1 pixel is bigger than the visible area
            self.imscale *= self.delta
            scale *= self.delta
        self.canvas.scale('all', x_wheel, y_wheel, scale, scale)  # rescale all canvas objects
        self.show_image()

    def show_image(self, event=None):
        """ Creating the canvas with the picture. """
        global bbox, bbox_2
        bbox_1 = self.canvas.bbox(self.container)  # get image area
        # Remove 1 pixel shift at the sides of the bbox1
        bbox_1 = (bbox_1[0] + 1, bbox_1[1] + 1, bbox_1[2] - 1, bbox_1[3] - 1)
        bbox_2 = (self.canvas.canvasx(0), self.canvas.canvasy(0), self.canvas.canvasx(self.canvas.winfo_width()),
                  self.canvas.canvasy(self.canvas.winfo_height()))
        bbox = [min(bbox_1[0], bbox_2[0]), min(bbox_1[1], bbox_2[1]), max(bbox_1[2], bbox_2[2]),
                max(bbox_1[3], bbox_2[3])]
        if bbox[0] == bbox_2[0] and bbox[2] == bbox_2[2]:  # whole image in the visible area
            bbox[0] = bbox_1[0]
            bbox[2] = bbox_1[2]
        if bbox[1] == bbox_2[1] and bbox[3] == bbox_2[3]:  # whole image in the visible area
            bbox[1] = bbox_1[1]
            bbox[3] = bbox_1[3]
        self.canvas.configure(scrollregion=bbox)  # set scroll region
        x_1 = max(bbox_2[0] - bbox_1[0], 0)  # get coordinates (x1,y1,x2,y2) of the image tile
        y_1 = max(bbox_2[1] - bbox_1[1], 0)
        x_2 = min(bbox_2[2], bbox_1[2]) - bbox_1[0]
        y_2 = min(bbox_2[3], bbox_1[3]) - bbox_1[1]
        if int(x_2 - x_1) > 0 and int(y_2 - y_1) > 0:  # show image if it in the visible area
            x_0 = min(int(x_2 / self.imscale), self.width)  # sometimes it is larger on 1 pixel...
            y_0 = min(int(y_2 / self.imscale), self.height)  # ...and sometimes not
            image = self.image.crop((int(x_1 / self.imscale), int(y_1 / self.imscale), x_0, y_0))
            imagetk = ImageTk.PhotoImage(image.resize((int(x_2 - x_1), int(y_2 - y_1))))
            imageid = self.canvas.create_image(max(bbox_2[0], bbox_1[0]), max(bbox_2[1], bbox_1[1]),
                                               anchor='nw', image=imagetk)
            self.canvas.lower(imageid)  # set image into background
            self.canvas.imagetk = imagetk  # keep an extra reference to prevent garbage-collection


class MainWindow(Frame):
    """ GUI design definitions. """
    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.member1 = ZoomAdvanced(parent)
        if os.path.isfile('directKiwi_server_list.db') is not True:
            tkMessageBox.showinfo(title="  (ツ) ", message="oops no node db found, Click OK to run an update now")
            CheckUpdate().run()
        global MODE
        # Run the Checkversion routine
        self.checkversion()
        bgc = '#999999'  # GUI background color  default #d9d9d9
        fgc = '#000000'  # GUI foreground color  default #000000
        dfgc = '#a3a3a3'  # GUI (disabled) foreground color
        # Bottom-Right control background
        self.ctrl_backgd = Label(parent)
        self.ctrl_backgd.place(relx=0, rely=0.8, relheight=0.3, relwidth=1)
        self.ctrl_backgd.configure(bg=bgc, fg=fgc, width=214)

        # Map Legend
        self.label01 = Label(parent)
        self.label01.place(x=0, y=0, height=14, width=85)
        self.label01.configure(bg=bgc, font="TkFixedFont 7", anchor="w", fg=STDCOLOR, text="█ Standard")
        self.label02 = Label(parent)
        self.label02.place(x=0, y=14, height=14, width=85)
        self.label02.configure(bg=bgc, font="TkFixedFont 7", anchor="w", fg=FAVCOLOR, text="█ Favorite")
        self.label03 = Label(parent)
        self.label03.place(x=0, y=28, height=14, width=85)
        self.label03.configure(bg=bgc, font="TkFixedFont 7", anchor="w", fg=BLKCOLOR, text="█ Blacklisted")
        self.label04 = Label(parent)
        self.label04.place(x=0, y=42, height=14, width=85)
        self.label04.configure(bg=bgc, font="TkFixedFont 7", anchor="w", fg="#001E00", text="█ no SNR data")
        # Control Legend
        self.label1 = Label(parent)
        self.label1.place(relx=0.605, rely=0.95)
        self.label1.configure(bg=bgc, font="TkFixedFont", fg=fgc, text="Freq:")
        self.label2 = Label(parent)
        self.label2.place(relx=0.72, rely=0.95)
        self.label2.configure(bg=bgc, font="TkFixedFont", fg=fgc, text="kHz")
        # Frequency entry field
        self.entry1 = Entry(parent)
        self.entry1.place(relx=0.65, rely=0.948, height=23, width=70)
        self.entry1.configure(bg="white", disabledforeground=dfgc, font="TkFixedFont", insertbackground=fgc, width=214)
        self.entry1.bind('<Control-a>', self.ctrla)
        # Stop Listen button
        self.stop_button = Button(parent)
        self.stop_button.place(relx=0.828, rely=0.95, height=24, width=80)
        self.stop_button.configure(activebackground=bgc, activeforeground=fgc, bg="red", disabledforeground=dfgc,
                                   fg="black", highlightbackground=bgc, highlightcolor=fgc, pady="0",
                                   text="Stop Listen", command=StopListen().run, state="disabled")
        # Update button
        self.update_button = Button(parent)
        self.update_button.place(relx=0.915, rely=0.95, height=24, width=80)
        self.update_button.configure(activebackground=bgc, activeforeground=fgc, bg="orange", disabledforeground=dfgc,
                                     fg="black", highlightbackground=bgc, highlightcolor=fgc, pady="0",
                                     text="update map", command=self.runupdate, state="normal")
        # Console window
        self.console_window = Text(parent)
        self.console_window.place(relx=0.000, rely=0.8, relheight=0.2, relwidth=0.590)
        self.console_window.configure(bg="black", font="TkTextFont", fg="red", highlightbackground=bgc,
                                      highlightcolor=fgc, insertbackground=fgc, selectbackground="#c4c4c4",
                                      selectforeground=fgc, undo="1", width=970, wrap="word")
        # Adding a scrollbar to console
        vsb2 = Scrollbar(parent, orient="vertical", command=self.console_window.yview)
        vsb2.place(relx=0.575, rely=0.8, relheight=0.2, width=16)
        self.console_window.configure(yscrollcommand=vsb2.set)
        # Low pass filter scale
        self.lowpass_scale = Scale(parent, from_=0, to=6000)
        self.lowpass_scale.place(relx=0.6, rely=0.8, relwidth=0.39, height=40)
        self.lowpass_scale.set(LP_CUT)
        self.lowpass_scale.configure(activebackground=bgc, background=bgc, foreground=fgc, highlightbackground=bgc,
                                     highlightcolor=bgc, orient="horizontal", showvalue="0", troughcolor=dfgc,
                                     resolution=10, label="Low Pass Filter (0Hz)", command=self.changelpvalue)
        # High pass filter scale
        self.highpass_scale = Scale(parent, from_=0, to=6000)
        self.highpass_scale.place(relx=0.6, rely=0.87, relwidth=0.39, height=40)
        self.highpass_scale.set(HP_CUT)
        self.highpass_scale.configure(activebackground=bgc, background=bgc, foreground=fgc, highlightbackground=bgc,
                                      highlightcolor=bgc, orient="horizontal", showvalue="0", troughcolor=dfgc,
                                      resolution=10, label="High Pass Filter (3600Hz)", command=self.changehpvalue)
        # Modulation Combobox
        self.modulation_box = ttk.Combobox(parent, state="readonly")
        self.modulation_box.place(relx=0.755, rely=0.948, height=24, relwidth=0.06)
        self.modulation_box.configure(font="TkTextFont", values=["USB", "LSB", "AM", "AMn", "CW", "CWn"])
        self.modulation_box.current(0)
        self.modulation_box.bind("<<ComboboxSelected>>", self.modechoice)
        MODE = 'USB'
        # Adding some texts to console window at program start
        self.writelog("This is " + VERSION + ", a GUI written for python 2.7 / Tk")
        self.writelog("Low Pass Cut Filter [" + str(LP_CUT) + "Hz] - High Pass Cut Filter [" + str(HP_CUT) + "Hz]")
        if AGC == 1:
            self.writelog("AGC is [ON]")
        elif AGC == 0 and HANG == 0:
            self.writelog("MGC is [ON] - [Gain " + str(MGAIN) + "dB] - Hang [OFF] - Threshold [" + str(
                THRESHOLD) + "dB] - Slope [" + str(SLOPE) + "dB] - Decay [" + str(DECAY).replace("\n", "") + "ms]")
        else:
            self.writelog("MGC is [ON] - Gain [" + str(MGAIN) + "dB] - Hang [ON] - Threshold [" + str(
                THRESHOLD) + "dB] - Slope [" + str(SLOPE) + "dB] - Decay [" + str(DECAY).replace("\n", "") + "ms]")
        self.writelog("There are [" + str(NODE_COUNT) + "] KiwiSDRs in the db. Have fun !")
        self.writelog("LEFT click : Start listening -=- RIGHT click : Get informations")
        #  GUI topbar menus
        menubar = Menu(self)
        parent.config(menu=menubar)
        # Audio Settings Menu
        menubar.add_command(label="Audio Settings", command=self.show_demod_config)
        # Map Settings Menu
        menu_1 = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Map Settings", menu=menu_1)
        sm1 = Menu(menu_1, tearoff=0)
        sm2 = Menu(menu_1, tearoff=0)
        menu_1.add_command(label='Change map', command=self.choose_map)  # map choice
        menu_1.add_cascade(label='Map Filters', menu=sm1, underline=0)  # map filters
        menu_1.add_cascade(label='Set Colors', menu=sm2, underline=0)  # node colors
        menu_1.add_command(label='Set Icon size', command=lambda *args: self.default_icon_size())  # icon size config
        sm1.add_command(label="All", command=lambda *args: [SaveCfg().save_cfg("map", "mapfl", 0), Restart().run()])
        sm1.add_command(label="Std+Fav", command=lambda *args: [SaveCfg().save_cfg("map", "mapfl", 1), Restart().run()])
        sm1.add_command(label="Fav", command=lambda *args: [SaveCfg().save_cfg("map", "mapfl", 2), Restart().run()])
        sm1.add_command(label="Black", command=lambda *args: [SaveCfg().save_cfg("map", "mapfl", 3), Restart().run()])
        sm2.add_command(label="Standard node color", command=lambda *args: [self.color_change(0), Restart().run()])
        sm2.add_command(label="Favorite node color", command=lambda *args: [self.color_change(1), Restart().run()])
        sm2.add_command(label="Blacklisted node color", command=lambda *args: [self.color_change(2), Restart().run()])
        # About Menu
        menu_2 = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="?", menu=menu_2)  # about menu
        menu_2.add_command(label="Help", command=self.help)
        menu_2.add_command(label="About", command=self.about)
        menu_2.add_command(label="Check for Update Now...", command=self.checkversion)
        # Purge Frequency entry box, waiting for the desired FREQUENCY (default=10000kHz)
        self.entry1.delete(0, 'end')

    def modechoice(self, event=None):
        """ Reading the typed FREQUENCY in the FREQUENCY entry box. """
        global MODE
        MODE = self.modulation_box.get()
        self.writelog("Modulation: " + str(MODE))

    def show_demod_config(self):
        """ KiwiSDR demodulation parameters window creation. """
        ReadCfg().read_cfg()
        tk_demod_cfg = Tk()
        tk_demod_cfg.title('KiwiSDR Demodulation Settings')
        tk_demod_cfg.resizable(False, False)
        demod_label = Message(tk_demod_cfg)
        demod_label.place(x=210, y=18)
        demod_label.configure(anchor="w",
                              text="Low Pass Filter (Hz)\n\n\nHigh Pass Filter (Hz)\n\n\n\n\nManual Gain (dB)\n\n\n"
                                   "Threshold (dBm)\n\n\nSlope\n\n\nDecay (ms)")
        scales_ui = []
        scales = {'lp_scale': ['0', '6000', '10', '0', '200', 'horizontal', '50', LP_CUT],
                  'hp_scale': ['0', '6000', '10', '44', '200', 'horizontal', '50', HP_CUT],
                  'gain_scale': ['0', '120', '10', '120', '200', 'horizontal', '1', MGAIN],
                  'thres_scale': ['-130', '0', '10', '164', '200', 'horizontal', '1', THRESHOLD],
                  'slope_scale': ['0', '10', '10', '209', '200', 'horizontal', '1', SLOPE],
                  'decay_scale': ['20', '5000', '10', '254', '200', 'horizontal', '10', DECAY]}
        scales = OrderedDict(sorted(scales.items()))
        for key, value in scales.items():
            key = Scale(tk_demod_cfg, from_=value[0], to=value[1])
            key.place(x=value[2], y=value[3], width=value[4])
            key.configure(orient=value[5], resolution=value[6])
            key.set(value[7])
            scales_ui.append(key)
        ctrlb = Button(tk_demod_cfg, command=lambda **kwargs: self.gc_button(ctrlb, tk_demod_cfg, agc=AGC))
        hangb = Button(tk_demod_cfg, command=lambda **kwargs: self.hang_button(hangb, hang=HANG))
        saveb = Button(tk_demod_cfg,
                       command=lambda **kwargs: self.save_demod_cfg(tk_demod_cfg, lp_cut=scales_ui[3].get(),
                                                                    hp_cut=scales_ui[2].get(),
                                                                    mgain=scales_ui[1].get(), thres=scales_ui[5].get(),
                                                                    slope=scales_ui[4].get(),
                                                                    decay=scales_ui[0].get(), hang=HANG, agc=AGC))
        ctrlb.place(x=10, y=100, height=20, width=198)
        ctrlb.configure(text="Automatic Gain Control: ON")
        hangb.place(x=214, y=100, height=20, width=50)
        hangb.configure(text="Hang")
        saveb.place(x=270, y=100, height=20, width=50)
        saveb.configure(text="Save", bg="red")
        if HANG == 1:
            hangb.configure(relief="sunken")
        else:
            hangb.configure(relief="raised")
        if AGC == 1:
            tk_demod_cfg.geometry("330x128+200+200")
            ctrlb.configure(text="Automatic Gain Control Active")
        else:
            tk_demod_cfg.geometry("330x310+200+200")
            ctrlb.configure(text="Manual Gain Control Active")

    @staticmethod
    def gc_button(ctrlb, tk_demod_cfg, **kwargs):
        """ DirectKiwi demodulation config window AGC/MGC button actions. """
        if kwargs.get('agc') == 1:
            tk_demod_cfg.geometry("330x310+200+200")
            ctrlb.configure(text="Manual Gain Control Active")
            APP.window2.save_demod_cfg(None, agc=0)
        else:
            tk_demod_cfg.geometry("330x128+200+200")
            ctrlb.configure(text="Automatic Gain Control Active")
            APP.window2.save_demod_cfg(None, agc=1)
        ReadCfg().read_cfg()

    @staticmethod
    def hang_button(hangb, **kwargs):
        """ DirectKiwi demodulation config window HANG button actions. """
        if kwargs.get('hang') == 1:
            hangb.configure(relief="raised")
            APP.window2.save_demod_cfg(None, hang=0)
        else:
            hangb.configure(relief="sunken")
            APP.window2.save_demod_cfg(None, hang=1)
        ReadCfg().read_cfg()

    @staticmethod
    def save_demod_cfg(tk_demod_cfg, **kwargs):
        """ Audio demodulation config window Save button actions. """
        if kwargs.get('lp_cut') is not None:
            APP.window2.changelpvalue(kwargs.get('lp_cut'))
            APP.window2.lowpass_scale.set(kwargs.get('lp_cut'))
        if kwargs.get('hp_cut') is not None:
            APP.window2.changehpvalue(kwargs.get('hp_cut'))
            APP.window2.highpass_scale.set(kwargs.get('hp_cut'))
        for key, value in kwargs.items():
            SaveCfg().save_cfg("demod", key, value)
        if tk_demod_cfg is not None:
            tk_demod_cfg.destroy()

    @staticmethod
    def changelpvalue(lpvalue):
        """ Adapt the high pass slider according to moved low pass slider (should not be higher). """
        global LP_CUT
        APP.window2.lowpass_scale.configure(label="Low Pass Filter (" + str(lpvalue) + "Hz)")
        if APP.window2.lowpass_scale.get() >= APP.window2.highpass_scale.get():
            APP.window2.highpass_scale.set(APP.window2.lowpass_scale.get() + 10)
            LP_CUT = APP.window2.lowpass_scale.get()
        else:
            LP_CUT = APP.window2.lowpass_scale.get()
        return LP_CUT

    @staticmethod
    def changehpvalue(hpvalue):
        """ Adapt the low pass slider according to moved high pass slider (should not be lower). """
        global HP_CUT
        APP.window2.highpass_scale.configure(label="High Pass Filter (" + str(hpvalue) + "Hz)")
        if APP.window2.highpass_scale.get() <= APP.window2.lowpass_scale.get():
            APP.window2.lowpass_scale.set(APP.window2.highpass_scale.get() - 10)
            HP_CUT = APP.window2.highpass_scale.get()
        else:
            HP_CUT = APP.window2.highpass_scale.get()
        return HP_CUT

    @staticmethod
    def ctrla(event):
        """ Allow ctrl+A in FREQUENCY box. """
        event.widget.select_range(0, 'end')
        event.widget.icursor('end')
        return 'break'

    def writelog(self, msg):
        """ The main console log text feed. """
        self.console_window.insert('end -1 lines',
                                   "[" + str(time.strftime('%H:%M.%S', time.gmtime())) + "] - " + msg + "\n")
        time.sleep(0.01)
        self.console_window.see('end')

    @staticmethod
    def help():
        """ Help menu text. """
        master = Tk()
        help_menu = Message(master, text="""
    1/ Enter a FREQUENCY and choose a modulation
    2/ Mouse click left on a node to start demodulating
    3/ Switch from node to node simply by click left on their icons
    4/ Other node informations are displayed if you click right on them
    """, width=1000, font="TkFixedFont 8", bg="white", anchor="center")
        help_menu.pack()

    @staticmethod
    def about():
        """ About menu text. """
        master = Tk()
        about_menu = Message(master, text="""
    Welcome to """ + VERSION + """

    The World map icons colors are static, click UPDATE button to get an fresh SNR-based colorized one
    KiwiSDR node informations are retrieved when node square icon is right-clicked on the map

    Thanks to Pierre Ynard (linkfanel) for the KiwiSDR network node listing used as source for GUI map update
    Thanks to Marco Cogoni (IS0KYB) for the KiwiSDR network SNR measurements listing used as source for GUI map update
    And.. Thanks to all KiwiSDR hosters...

    linkz 

    feedback, features request or help : contact me at ounaid at gmail dot com or IRC freenode #wunclub / #priyom
    """, width=1000, font="TkFixedFont 8", bg="white", anchor="center")
        about_menu.pack()

    def default_icon_size(self):
        """ Change map icon size config window. """
        global ICON_CFG
        ICON_CFG = Tk()
        ICON_CFG.geometry("280x50+50+50")
        ICON_CFG.title('Default Icon size')
        icon_slider = Scale(ICON_CFG, from_=2, to=10)
        icon_slider.place(x=10, y=0, width=200, height=100)
        icon_slider.configure(orient="horizontal", showvalue="1", resolution=1, label="")
        icon_slider.set(ICONSIZE)
        icon_save_button = Button(ICON_CFG, command=lambda *args: self.set_default_icon_size(icon_slider.get()))
        icon_save_button.place(x=220, y=20, height=20)
        icon_save_button.configure(text="Save")

    @staticmethod
    def set_default_icon_size(isize):
        """ Save choosed icon size to config file. """
        APP.window2.writelog("Icon size set to " + str(isize))
        SaveCfg().save_cfg("map", "iconsize", isize)
        ICON_CFG.destroy()
        Restart().run()

    @staticmethod
    def color_change(value):
        """ Ask for a color and save to config file. """
        color_n = askcolor()
        color_n = color_n[1]
        if color_n:
            if value == 0:
                SaveCfg().save_cfg("map", "std", color_n)
            elif value == 1:
                SaveCfg().save_cfg("map", "fav", color_n)
            else:
                SaveCfg().save_cfg("map", "blk", color_n)
        else:
            pass

    @staticmethod
    def choose_map():
        """ Change map menu and Save to config file. """
        mapname = tkFileDialog.askopenfilename(initialdir="maps")
        if not mapname or not mapname.lower().endswith(('.png', '.jpg', '.jpeg')):
            tkMessageBox.showinfo("", message="Error, select png/jpg/jpeg files only.\n Loading default map now.")
            mapname = "maps/directKiwi_map_grayscale_with_sea.jpg"
        SaveCfg().save_cfg("map", "file", "maps/" + os.path.split(mapname)[1])
        Restart().run()

    def runupdate(self):
        """ Run update check when button is pushed. """
        self.update_button.configure(state="disabled")
        CheckUpdate(self).start()

    @staticmethod
    def checkversion():
        """ Watch on github if a new version has been released (1st line of README.md parsed). """
        try:
            checkver = requests.get('https://raw.githubusercontent.com/llinkz/directKiwi/master/README.md', timeout=2)
            gitsrctext = checkver.text.split("\n")
            if float(gitsrctext[0][2:].split("v", 1)[1]) > float(VERSION.split("v", 1)[1][:4]):
                tkMessageBox.showinfo(title="UPDATE INFORMATION", message=str(gitsrctext[0][2:]) + " released !")
            else:
                pass
        except (ImportError, requests.RequestException):
            print "Unable to verify version information. Sorry."


class MainW(Tk, object):
    """ Creating the Tk GUI design. """
    def __init__(self):
        Tk.__init__(self)
        Tk.option_add(self, '*Dialog.msg.font', 'TkFixedFont 7')
        self.window = ZoomAdvanced(self)
        self.window2 = MainWindow(self)


def on_closing():
    """ Actions to perform when software is closed using the top-right check button. """
    global CLIENT_PID
    if tkMessageBox.askokcancel("Quit", "Do you want to quit?"):
        try:  # to kill kiwirecorder.py
            os.kill(CLIENT_PID, signal.SIGTERM)
        except (NameError, OSError):
            print ""
        else:
            os.kill(CLIENT_PID, signal.SIGTERM)
        os.kill(os.getpid(), signal.SIGTERM)
        APP.destroy()


class Restart(object):
    """ GUI Restart routine. """
    def __init__(self):
        pass

    def __str__(self):
        return self.__class__.__name__

    @staticmethod
    def run():
        """ GUI Restart routine. """
        global CLIENT_PID
        try:
            os.kill(CLIENT_PID, signal.SIGTERM)
        except (NameError, OSError):
            print ".Restarting GUI."
        else:
            os.kill(CLIENT_PID, signal.SIGTERM)
        os.execv(sys.executable, [sys.executable] + sys.argv)


if __name__ == '__main__':
    APP = MainW()
    APP.title(VERSION)
    APP.protocol("WM_DELETE_WINDOW", on_closing)
    APP.mainloop()
