#!/usr/bin/python
# -*- coding: utf-8 -*-

import codecs
import json
import os
import ttk
import requests
import signal
import subprocess
import threading
import time
import tkFileDialog
import tkMessageBox
import unicodedata
import webbrowser
from Tkinter import *
from shutil import copyfile
from subprocess import PIPE
from tkColorChooser import askcolor

from PIL import Image, ImageTk

VERSION = "directKiwi v4.00"


class Restart:
    def __init__(self):
        pass

    @staticmethod
    def run():
        global proc_pid
        try:  # to kill kiwirecorder.py process if exists
            os.kill(proc_pid, signal.SIGTERM)
        except:
            pass
        os.execv(sys.executable, [sys.executable] + sys.argv)  # restart directKiwi.py


class CheckUpdate(threading.Thread):
    def __init__(self, parent=None):
        super(CheckUpdate, self).__init__()
        self.parent = parent

    def run(self):
        pierre_is_ok = "no"
        marco_is_ok = "no"
        print "Checking if web sources are up, wait a moment..."
        try:
            checklinkfanel = requests.get("http://rx.linkfanel.net/kiwisdr_com.js", timeout=2)
            if checklinkfanel.status_code == 200:
                pierre_is_ok = "yes"
                print "http://rx.linkfanel.net/ is up"
        except:
            pass
        try:
            checkmarco = requests.get("http://sibamanna.duckdns.org/snrmap_4bands.json", timeout=2)
            if checkmarco.status_code == 200:
                marco_is_ok = "yes"
                print "http://sibamanna.duckdns.org/ is up"
        except:
            pass
        if pierre_is_ok == "no" and marco_is_ok == "yes":
            print "Pierre's website is not reachable. Node listing update is not possible, try later."
        elif pierre_is_ok == "yes" and marco_is_ok == "no":
            print "Marco's website is not reachable. Node listing update is not possible, try later."
        elif pierre_is_ok == "no" and marco_is_ok == "no":
            print "Both Marco's & Pierre's websites are not reachable. Node listing update is not possible, try later."
        else:
            print "MAP update in progress...please wait until software restart.."
            RunUpdate().run()


class RunUpdate(threading.Thread):
    def __init__(self, parent=None):
        super(RunUpdate, self).__init__()
        self.parent = parent

    def run(self):
        try:
            nodelist = requests.get("http://rx.linkfanel.net/kiwisdr_com.js")  # getting the full KiwiSDR node list
            json_data = json.loads(nodelist.text[nodelist.text.find('['):].replace('},\n]\n;\n', '}]'))
            # Important info concerning UPDATE FAIL errors:
            # Sometimes some nodes datas are incompletely returned to kiwisdr.com/public so below is a dirty way to
            # bypass them, using their mac address.
            # ATM mac should be manually found in http://rx.linkfanel.net/kiwisdr_com.js webpage source code, search
            # using the line number returned by the update FAIL error text, will try to fix one day ....
            # json_data = json.loads(nodelist.text[nodelist.text.find('['):].replace('},\n]\n;\n', '}]').replace('985dad7f54fc\",','985dad7f54fc\"'))
            # json_data = json.loads(nodelist.text)  # when kiwisdr_com.js will be in real json format
            snrlist = requests.get("http://sibamanna.duckdns.org/snrmap_4bands.json")
            json_data2 = json.loads(snrlist.text)
            try:
                linkz_status = requests.get("http://linkz.ddns.net:8073/status", timeout=3)
                s_fix = re.search('fixes_min=(.*)', linkz_status.text)
                l_fixes = s_fix.group(1)
            except:
                l_fixes = 0
                pass
            if os.path.isfile('directKiwi_server_list.db') is True:
                os.remove('directKiwi_server_list.db')
            with codecs.open('directKiwi_server_list.db', 'w', encoding='utf8') as g:
                g.write("[\n")
                for i in range(len(json_data)):  # parse all nodes from linkfanel website / json db

                    for index, element in enumerate(json_data2['features']):  # check IS0KYB db
                        if json_data[i]['id'] in json.dumps(json_data2['features'][index]):
                            if json_data[i]['tdoa_id'] == '':
                                node_id = json_data[i]['url'].split('//', 1)[1].split(':', 1)[0].replace(".",
                                                                                                         "").replace(
                                    "-", "").replace("proxykiwisdrcom", "").replace("ddnsnet", "")
                                try:
                                    ipfield = re.search(
                                        r'\b((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\b',
                                        json_data[i]['url'].split('//', 1)[1].split(':', 1)[0])
                                    node_id = "ip" + str(ipfield.group(1)).replace(".", "")
                                except:
                                    pass
                                try:
                                    hamcallfield = re.search(
                                        r"(.*)(\s|,|\/|^)([A-Za-z]{1,2}[0-9][A-Za-z]{1,3})(\s|,|\/|\@|\-)(.*)",
                                        json_data[i]['name'])
                                    node_id = hamcallfield.group(3).upper()
                                except:
                                    pass
                            else:
                                node_id = json_data[i]['tdoa_id']
                            try:
                                gpsfield = re.search(
                                    r"([-+]?[0-9]{1,2}(\.[0-9]*)?)(,| ) ?([-+]?[0-9]{1,3}(\.[0-9]*))?",
                                    json_data[i]['gps'][1:-1])
                                nodelat = gpsfield.group(1)
                                nodelon = gpsfield.group(4)
                            except:
                                # Admins not respecting KiwiSDR admin page GPS field format (nn.nnnnnn, nn.nnnnnn)
                                # => nodes will be shown at top-right map edge, as it fails the update code process
                                print "*** Error reading <gps> field : >> " + str(
                                    unicodedata.normalize("NFKD", json_data[i]['gps'][1:-1]).encode("ascii",
                                                                                                    "ignore")) + " << for \"" + unicodedata.normalize(
                                    "NFKD", json_data[i]["name"]).encode("ascii", "ignore") + "\""
                                print "*** This node will be displayed at 0N 0E position"
                                nodelat = "0"
                                nodelon = "0"
                            # (-?(90[:°d] * 00[:\'\'m]*00(\.0+)?|[0-8][0-9][ :°d]*[0-5][0-9][ :\'\'m]*[0-5][0-9](\.\d+)?)[ :\?\"s]*(N|n|S|s)?)[ ,]*(-?(180[ :°d]*00[ :\'\'m]*00(\.0+)?|(1[0-7][0-9]|0[0-9][0-9])[ :°d]*[0-5][0-9][ :\'\'m]*[0-5][0-9](\.\d+)?)[ :\?\"s]*(E|e|W|w)?)
                            g.write(' { \"mac\":\"' + json_data[i]['id'] + '\", \"url\":\"' +
                                    json_data[i]['url'].split('//', 1)[1] + '\", \"gps\":\"' + json_data[i][
                                        'fixes_min'] + '\", \"id\":\"' + node_id + '\", \"lat\":\"' + nodelat + '\", \"lon\":\"' + nodelon + '\", \"name\":\"' + unicodedata.normalize(
                                "NFKD", json_data[i]["name"]).encode("ascii", "ignore").replace("\"",
                                                                                                "") + '\", \"users\":\"' +
                                    json_data[i]['users'] + '\", \"usersmax\":\"' + json_data[i][
                                        'users_max'] + '\", \"snr1\":\"' + str(
                                element['properties']['snr1_avg']) + '\", \"snr2\":\"' + str(
                                element['properties']['snr2_avg']) + '\", \"snr3\":\"' + str(
                                element['properties']['snr3_avg']) + '\", \"snr4\":\"' + str(
                                element['properties']['snr4_avg']) + '\", \"nlvl1\":\"' + str(
                                element['properties']['bg1_avg']) + '\", \"nlvl2\":\"' + str(
                                element['properties']['bg2_avg']) + '\", \"nlvl3\":\"' + str(
                                element['properties']['bg3_avg']) + '\", \"nlvl4\":\"' + str(
                                element['properties']['bg4_avg']) + '\"},\n')
                        else:
                            pass
                # here is the hardcode for my own KiwiSDR, it will soon include real SNR/noise values.. thx Marco
                g.write(' { "mac":"04a316df1bca", "url":"linkz.ddns.net:8073", "gps":"' + str(
                    l_fixes) + '", "id":"linkz", "lat":"45.4", "lon":"5.3", "name":"directKiwi GUI developer, French Alps", "users":"0", "usersmax":"4", "snr1":"0", "snr2":"0", "snr3":"0", "snr4":"0", "nlvl1":"0", "nlvl2":"0", "nlvl3":"0", "nlvl4":"0"}\n]')
                g.close()
                # normally if update process is ok, we can make a backup copy of the server listing
                copyfile("directKiwi_server_list.db", "directKiwi_server_list.db.bak")
                Restart().run()
        except Exception as e:
            print e
            print "UPDATE FAIL, sorry"


class ReadConfigFile:
    @staticmethod
    def read_cfg():
        global dx0, dy0, dx1, dy1, dmap, mapfl, white, black, colorline, defaultbw
        global lp_cut, hp_cut, autoagcactive, hang, managcgain, threshold, slope, decay
        with open('directKiwi.cfg', "r") as c:
            try:
                configline = c.readlines()
                dx0 = configline[3].split(',')[0]  # longitude min
                dy0 = configline[3].split(',')[1]  # latitude max
                dx1 = configline[3].split(',')[2]  # longitude max
                dy1 = configline[3].split(',')[3]  # latitude min
                dmap = configline[5].split('\n')[0]  # displayed map
                mapfl = configline[7].replace("\n", "").split(',')[0]  # map filter
                white = configline[9].replace("\n", "").split(',')  # nodes whitelist
                black = configline[11].replace("\n", "").split(',')  # nodes blacklist
                colorline = configline[13].replace("\n", "").split(',')  # GUI map colors
                lp_cut = configline[15].split(',')[0]  # lp cut
                hp_cut = configline[15].split(',')[1]  # hp cut
                autoagcactive = configline[15].split(',')[2]  # 1=AGC  0=MGC
                hang = configline[15].split(',')[3]  # hang
                managcgain = configline[15].split(',')[4]  # MGC gain
                threshold = configline[15].split(',')[5]  # Threshold
                slope = configline[15].split(',')[6]  # slope
                decay = configline[15].split(',')[7]  # decay
            except:
                copyfile("directKiwi.cfg", "directKiwi.cfg.bak")
                sys.exit(
                    "Oops, something is wrong with the directKiwi.cfg config file format\nIf you have just updated, make sure all the required lines are present.\nYou can keep your directKiwi.cfg file and add the missing lines manually in order to keep your settings intact.\nCheck https://raw.githubusercontent.com/llinkz/directKiwi/master/directKiwi.cfg for a sample.\nNote: a backup copy of your config file has been created as directKiwi.cfg.bak")
        c.close()


class SaveConfigFile:
    @staticmethod
    def save_cfg(field, input):
        global dmap, mapfl, white, black, colorline, defaultbw
        global lp_cut, hp_cut, autoagcactive, hang, managcgain, threshold, slope, decay
        with open('directKiwi.cfg', "w") as u:
            u.write("This is " + VERSION + " config file\n")
            u.write(
                "This file should be generated by directKiwi software only, in case something went wrong you can find a sample here: https://raw.githubusercontent.com/llinkz/directKiwi/master/directKiwi.cfg\n")
            u.write("# Default map geometry \n%s,%s,%s,%s\n" % (bbox2[0], bbox2[1], bbox2[2], bbox2[3]))
            if field == "mapc":
                u.write("# Default map picture \n%s\n" % input)
            else:
                u.write("# Default map picture \n%s\n" % dmap)
            if field == "mapfl":
                u.write(
                    "# Default map filter (0= All  1= Standard+Favorites  2= Favorites  3= Blacklisted) \n%s\n" % (
                        input))
            else:
                u.write(
                    "# Default map filter (0= All  1= Standard+Favorites  2= Favorites  3= Blacklisted) \n%s\n" % (
                        mapfl))
            u.write("# Whitelist \n%s\n" % ','.join(white))
            u.write("# Blacklist \n%s\n" % ','.join(black))
            if field == "nodecolor":
                u.write("# Default Colors (standard,favorites,blacklisted,known) \n%s\n" % input)
            else:
                u.write("# Default Colors (standard,favorites,blacklisted,known) \n%s\n" % ','.join(colorline))
            if field == "lp_cut":
                u.write(
                    "# Default Audio Settings (LP,HP,AGC/MGC,HANG,GAIN,THRESHOLD,SLOPE,DECAY) \n%s,%s,%s,%s,%s,%s,%s,%s" % (
                        input, hp_cut, autoagcactive, hang, managcgain, threshold, slope, decay))
            elif field == "hp_cut":
                u.write(
                    "# Default Audio Settings (LP,HP,AGC/MGC,HANG,GAIN,THRESHOLD,SLOPE,DECAY) \n%s,%s,%s,%s,%s,%s,%s,%s" % (
                        lp_cut, input, autoagcactive, hang, managcgain, threshold, slope, decay))
            elif field == "autoagcactive":
                u.write(
                    "# Default Audio Settings (LP,HP,AGC/MGC,HANG,GAIN,THRESHOLD,SLOPE,DECAY) \n%s,%s,%s,%s,%s,%s,%s,%s" % (
                        lp_cut, hp_cut, input, hang, managcgain, threshold, slope, decay))
            elif field == "hang":
                u.write(
                    "# Default Audio Settings (LP,HP,AGC/MGC,HANG,GAIN,THRESHOLD,SLOPE,DECAY) \n%s,%s,%s,%s,%s,%s,%s,%s" % (
                        lp_cut, hp_cut, autoagcactive, input, managcgain, threshold, slope, decay))
            elif field == "managcgain":
                u.write(
                    "# Default Audio Settings (LP,HP,AGC/MGC,HANG,GAIN,THRESHOLD,SLOPE,DECAY) \n%s,%s,%s,%s,%s,%s,%s,%s" % (
                        lp_cut, hp_cut, autoagcactive, hang, input, threshold, slope, decay))
            elif field == "threshold":
                u.write(
                    "# Default Audio Settings (LP,HP,AGC/MGC,HANG,GAIN,THRESHOLD,SLOPE,DECAY) \n%s,%s,%s,%s,%s,%s,%s,%s" % (
                        lp_cut, hp_cut, autoagcactive, hang, managcgain, input, slope, decay))
            elif field == "slope":
                u.write(
                    "# Default Audio Settings (LP,HP,AGC/MGC,HANG,GAIN,THRESHOLD,SLOPE,DECAY) \n%s,%s,%s,%s,%s,%s,%s,%s" % (
                        lp_cut, hp_cut, autoagcactive, hang, managcgain, threshold, input, decay))
            elif field == "decay":
                u.write(
                    "# Default Audio Settings (LP,HP,AGC/MGC,HANG,GAIN,THRESHOLD,SLOPE,DECAY) \n%s,%s,%s,%s,%s,%s,%s,%s" % (
                        lp_cut, hp_cut, autoagcactive, hang, managcgain, threshold, slope, input))
            else:
                u.write(
                    "# Default Audio Settings (LP,HP,AGC/MGC,HANG,GAIN,THRESHOLD,SLOPE,DECAY) \n%s,%s,%s,%s,%s,%s,%s,%s" % (
                        lp_cut, hp_cut, autoagcactive, hang, managcgain, threshold, slope, decay))
            u.close()


class StartKiwiSDRclient(threading.Thread):
    def __init__(self, parent=None):
        super(StartKiwiSDRclient, self).__init__()
        self.parent = parent

    def run(self):
        global parent, kiwisdrclient_pid, server_host, server_port, frequency, listenmode, dd, line
        global lp_cut, hp_cut, autoagcactive, hang, managcgain, threshold, slope, decay
        try:
            #  '-g', '1', '50', '0', '-100', '6', '1000'  <==== static AGC settings
            #  1= AGC (on)  50=Manual Gain (dB) 0=Hang (off)  -100=Threshold (dB) 6=Slope (dB) 1000=Decay (ms)
            #  -L and -H are demod filters settings, values are override by kiwiSDRclient.py (BW=3600Hz)
            proc8 = subprocess.Popen(
                [sys.executable, 'KiwiSDRclient.py', '-s', str(server_host), '-p', str(server_port), '-f',
                 str(frequency),
                 '-m', dd, '-L', str(lp_cut), '-H', str(hp_cut), '-g', str(autoagcactive), str(managcgain),
                 str(hang), str(threshold), str(slope), str(decay)], stdout=PIPE, shell=False)

            # proc8 = subprocess.Popen(
            #     [sys.executable, 'KiwiSDRclient.py', '-s', str(server_host), '-p', str(server_port), '-f',
            #      str(frequency), '-m', dd, '-L', '0', '-H', '5000', '-g', '1', '50', '0', '-100', '6', '1000'],
            #     stdout=PIPE, shell=False)
            kiwisdrclient_pid = proc8.pid
            listenmode = "1"
            app.window2.writelog(
                "Starting Listen mode    [ " + server_host + " / " + frequency + " kHz / " + str(dd).upper() + " ]")
        except:
            print "error: unable to demodulate this node"
            listenmode = "0"

        while True:
            line = proc8.stdout.readline()
            if line != '':
                if "-" not in line and "array" not in line:
                    try:
                        app.window2.writelog(line.rstrip())  # KiwiSDRclient.py stdout (node parameters)
                    except:
                        pass
                if "-" in line and "array" not in line:  # RSSI int values, those are negative and between -120 and -10
                    try:
                        app.window2.label3.configure(text=" " + str(int(line.rstrip())) + " dBm")
                        app.window2.feedsmeter(int(line.rstrip()) + 124)  # sends RSSI value to feed the smeter
                    except:
                        pass
            else:
                break


class FillMapWithNodes:
    def __init__(self, parent=None):
        self.parent = parent

    def run(self):
        global manual_bound_x, manual_bound_y, manual_bound_xsize, manual_bound_ysize, map_manual, nodecount, node_color
        if os.path.isfile('directKiwi_server_list.db') is True:
            with open('directKiwi_server_list.db') as f:
                db_data = json.load(f)
                nodecount = len(db_data)
                for i in range(nodecount):
                    # time.sleep(0.02)
                    try:
                        temp_snr_avg = (int(db_data[i]["snr1"]) + int(db_data[i]["snr2"]) + int(
                            db_data[i]["snr3"]) + int(db_data[i]["snr4"])) / 4
                        if db_data[i]["mac"] in white:  # favorite node color
                            node_color = (self.color_variant(colorline[1], (int(temp_snr_avg) - 45) * 5))
                        elif db_data[i]["mac"] in black:  # blacklist node color
                            node_color = (self.color_variant(colorline[2], (int(temp_snr_avg) - 45) * 5))
                        else:  # standard node color
                            node_color = (self.color_variant(colorline[0], (int(temp_snr_avg) - 45) * 5))
                    except Exception as e:
                        pass
                    try:
                        if mapfl == "1" and db_data[i]["mac"] not in black:
                            self.add_point(self.convert_lat(db_data[i]["lat"]), self.convert_lon(db_data[i]["lon"]),
                                           node_color, db_data[i]["url"], db_data[i]["mac"], db_data[i]["id"],
                                           db_data[i]["name"].replace(" ", "_").replace("!", "_"), db_data[i]["users"],
                                           db_data[i]["usersmax"], db_data[i]["gps"], db_data[i]["snr1"],
                                           db_data[i]["snr2"], db_data[i]["snr3"], db_data[i]["snr4"],
                                           db_data[i]["nlvl1"], db_data[i]["nlvl2"], db_data[i]["nlvl3"],
                                           db_data[i]["nlvl4"])
                        elif mapfl == "2" and db_data[i]["mac"] in white:
                            self.add_point(self.convert_lat(db_data[i]["lat"]), self.convert_lon(db_data[i]["lon"]),
                                           node_color, db_data[i]["url"], db_data[i]["mac"], db_data[i]["id"],
                                           db_data[i]["name"].replace(" ", "_").replace("!", "_"), db_data[i]["users"],
                                           db_data[i]["usersmax"], db_data[i]["gps"], db_data[i]["snr1"],
                                           db_data[i]["snr2"], db_data[i]["snr3"], db_data[i]["snr4"],
                                           db_data[i]["nlvl1"], db_data[i]["nlvl2"], db_data[i]["nlvl3"],
                                           db_data[i]["nlvl4"])
                        elif mapfl == "3" and db_data[i]["mac"] in black:
                            self.add_point(self.convert_lat(db_data[i]["lat"]), self.convert_lon(db_data[i]["lon"]),
                                           node_color, db_data[i]["url"], db_data[i]["mac"], db_data[i]["id"],
                                           db_data[i]["name"].replace(" ", "_").replace("!", "_"), db_data[i]["users"],
                                           db_data[i]["usersmax"], db_data[i]["gps"], db_data[i]["snr1"],
                                           db_data[i]["snr2"], db_data[i]["snr3"], db_data[i]["snr4"],
                                           db_data[i]["nlvl1"], db_data[i]["nlvl2"], db_data[i]["nlvl3"],
                                           db_data[i]["nlvl4"])
                        elif mapfl == "0":
                            self.add_point(self.convert_lat(db_data[i]["lat"]), self.convert_lon(db_data[i]["lon"]),
                                           node_color, db_data[i]["url"], db_data[i]["mac"], db_data[i]["id"],
                                           db_data[i]["name"].replace(" ", "_").replace("!", "_"), db_data[i]["users"],
                                           db_data[i]["usersmax"], db_data[i]["gps"], db_data[i]["snr1"],
                                           db_data[i]["snr2"], db_data[i]["snr3"], db_data[i]["snr4"],
                                           db_data[i]["nlvl1"], db_data[i]["nlvl2"], db_data[i]["nlvl3"],
                                           db_data[i]["nlvl4"])
                    except Exception as e:
                        print e
                        pass
        self.parent.canvas.scan_dragto(-int(dx0.split('.')[0]), -int(dy0.split('.')[0]), gain=1)  # adjust map pos.
        self.parent.show_image()

    # @staticmethod
    def convert_lat(self, lat):
        if float(lat) > 0:  # nodes are between LATITUDE 0 and 90N
            return 987.5 - (float(lat) * 11)
        else:  # nodes are between LATITUDE 0 and 60S
            return 987.5 + (float(0 - float(lat)) * 11)

    # @staticmethod
    def convert_lon(self, lon):
        return 1907.5 + ((float(lon) * 1910) / 180)

    # @staticmethod
    def color_variant(self, hex_color, brightness_offset=1):
        # source : https://chase-seibert.github.io/blog/2011/07/29/python-calculate-lighterdarker-rgb-colors.html
        rgb_hex = [hex_color[x:x + 2] for x in [1, 3, 5]]
        new_rgb_int = [int(hex_value, 16) + brightness_offset for hex_value in rgb_hex]
        new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int]
        return "#" + "".join(["0" + hex(i)[2:] if len(hex(i)[2:]) < 2 else hex(i)[2:] for i in new_rgb_int])

    def add_point(self, a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r):
        #  a   b    c    d   e   f   g    h     i     j   k    l    m    n    o   p   q   r
        # lon lat color host mac id name user usermx gps snr1 snr2 snr3 snr4 bg1 bg2 bg3 bg4
        try:
            self.parent.canvas.create_rectangle(float(b), float(a), float(b) + 5, float(a) + 5, fill=str(c),
                                                outline="black", activefill='white', tag=str(
                    '$'.join(map(str, [d, e, f, g, h, i, j, k, l, m, n, o, p, q, r]))))
            self.parent.canvas.tag_bind(str('$'.join(map(str, [d, e, f, g, h, i, j, k, l, m, n, o, p, q, r]))),
                                        "<Button-1>", self.parent.onClick)
        except Exception as error_add_point:
            print error_add_point


class ZoomAdvanced(Frame):  # src stackoverflow.com/questions/41656176/tkinter-canvas-zoom-move-pan?noredirect=1&lq=1 :)
    def __init__(self, parent):
        Frame.__init__(self, parent=None)
        parent.geometry("1050x600+200+50")
        global dx0, dy0, dx1, dy1, listenmode
        global dmap, host, white, black, mapfl
        ReadConfigFile().read_cfg()
        listenmode = "0"
        self.x = self.y = 0
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
        self.canvas.bind('<Button-5>', self.wheel)  # Linux Zoom disabled in this version !
        self.canvas.bind('<Button-4>', self.wheel)  # Linux Zoom disabled in this version !
        self.image = Image.open(dmap)
        self.width, self.height = self.image.size
        self.imscale = 1.0  # scale for the image
        self.delta = 2.0  # zoom magnitude
        # Put image into container rectangle and use it to set proper coordinates to the image
        self.container = self.canvas.create_rectangle(0, 0, self.width, self.height, width=0)
        self.canvas.config(scrollregion=(0, 0, self.width, self.height))
        self.start_x = None
        self.start_y = None
        self.canvas.scan_dragto(-int(dx0.split('.')[0]), -int(dy0.split('.')[0]), gain=1)  # adjust map pos.
        self.show_image()
        time.sleep(0.2)
        FillMapWithNodes(self).run()

    def displaySNR(self):  # work in progress
        pass

    def onClick(self, event):  # host sub menus
        global snrcheck, snrhost, host, white, black, listenmode, frequency
        host = self.canvas.gettags(self.canvas.find_withtag(CURRENT))[0]
        self.menu = Menu(self, tearoff=0, fg="black", bg="grey", font='TkFixedFont 7')
        self.menu2 = Menu(self.menu, tearoff=0, fg="black", bg="white", font='TkFixedFont 7')
        #  host.rsplit("$", 14)[#] <<
        #  0=host  1=id  2=short name  3=name  4=users  5=users max  6=GPS fix/min
        #  7=SNR 0-2 MHz  8=SNR 2-10 MHz  9=SNR 10-20 MHz  10=SNR 20-30 MHz
        #  11=Noise 0-2 MHz  12=Noise 2-10 MHz 13=Noise 10-20 MHz  14=Noise 20-30 MHz
        temp_snr_avg = (int(host.rsplit("$", 14)[7]) + int(host.rsplit("$", 14)[8]) + int(
            host.rsplit("$", 14)[9]) + int(host.rsplit("$", 14)[10])) / 4
        temp_noise_avg = (int(host.rsplit("$", 14)[11]) + int(host.rsplit("$", 14)[12]) + int(
            host.rsplit("$", 14)[13]) + int(host.rsplit("$", 14)[14])) / 4
        font_snr1 = font_snr2 = font_snr3 = font_snr4 = 'TkFixedFont 7'
        frequency = app.window2.Entry1.get()
        try:  # check if the node is answering
            chktimeout = 1  # timeout of the node check
            checkthenode = requests.get("http://" + str(host).rsplit("$", 14)[0] + "/status", timeout=chktimeout)
            infonodes = checkthenode.text.split("\n")
            try:  # node filtering
                permit_web = "no"
                is_gps_ok = "no"
                if infonodes[6].rsplit("=", 2)[1] == infonodes[7].rsplit("=", 2)[1]:  # users Vs. users_max
                    self.menu.add_command(label=str(host).rsplit("$", 14)[2] + " node have no available slots",
                                          background=(self.color_variant("#FF0000", (int(temp_snr_avg) - 50) * 5)),
                                          foreground=self.get_font_color(
                                              (self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                                          command=None)
                elif infonodes[1].rsplit("=", 2)[1] == "yes":  # offline=no/yes
                    self.menu.add_command(label=str(host).rsplit("$", 14)[2] + " node is currently offline",
                                          background=(self.color_variant("#FF0000", (int(temp_snr_avg) - 50) * 5)),
                                          foreground=self.get_font_color(
                                              (self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                                          command=None)
                else:  # all ok for this node
                    permit_web = "yes"
                    is_gps_ok = "yes"

            except Exception:
                if "not found" in infonodes[13]:
                    self.menu.add_command(
                        label=str(host).rsplit("$", 14)[2] + " node is not available. (proxy.kiwisdr.com error)",
                        background=(self.color_variant("#FF0000", (int(temp_snr_avg) - 50) * 5)),
                        foreground=self.get_font_color((self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                        command=None)
                    permit_web = "no"

        except requests.RequestException as reqerr:
            try:  # trying to deal with requests exceptions texts...
                reqer = \
                    str(reqerr.message).replace("'", "").replace(",", "").replace(":", "").replace("))", "").rsplit(">",
                                                                                                                    2)[
                        1]
            except:
                reqer = str(reqerr.message).rsplit(":", 1)[1]
            self.menu.add_command(label=str(host).rsplit("$", 14)[2] + " node is not available. " + str(reqer),
                                  background=(self.color_variant("#FF0000", (int(temp_snr_avg) - 50) * 5)),
                                  foreground=self.get_font_color(
                                      (self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))), command=None)
            permit_web = "no"

        if permit_web == "yes" and listenmode == "0" and frequency != "" and 5 < float(frequency) < 30000:
            self.menu.add_cascade(
                label="Listen using " + str(host).rsplit("$", 14)[0],
                state=NORMAL, background=(self.color_variant(colorline[0], (int(temp_snr_avg) - 50) * 5)),
                foreground=self.get_font_color((self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                menu=self.menu2)
            self.menu2.add_command(label="USB",
                                   background=(self.color_variant(colorline[0], (int(temp_snr_avg) - 50) * 5)),
                                   foreground=self.get_font_color(
                                       (self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                                   command=lambda *args: self.listenmode("usb"))
            self.menu2.add_command(label="LSB",
                                   background=(self.color_variant(colorline[0], (int(temp_snr_avg) - 50) * 5)),
                                   foreground=self.get_font_color(
                                       (self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                                   command=lambda *args: self.listenmode("lsb"))
            self.menu2.add_command(label="AM",
                                   background=(self.color_variant(colorline[0], (int(temp_snr_avg) - 50) * 5)),
                                   foreground=self.get_font_color(
                                       (self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                                   command=lambda *args: self.listenmode("am"))
            self.menu2.add_command(label="AMn",
                                   background=(self.color_variant(colorline[0], (int(temp_snr_avg) - 50) * 5)),
                                   foreground=self.get_font_color(
                                       (self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                                   command=lambda *args: self.listenmode("amn"))
            self.menu2.add_command(label="CW",
                                   background=(self.color_variant(colorline[0], (int(temp_snr_avg) - 50) * 5)),
                                   foreground=self.get_font_color(
                                       (self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                                   command=lambda *args: self.listenmode("cw"))
            self.menu2.add_command(label="CWn",
                                   background=(self.color_variant(colorline[0], (int(temp_snr_avg) - 50) * 5)),
                                   foreground=self.get_font_color(
                                       (self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                                   command=lambda *args: self.listenmode("cwn"))

        if listenmode == "1":
            self.menu.add_command(
                label="Stop Listen Mode",
                state=NORMAL, background=(self.color_variant(colorline[0], (int(temp_snr_avg) - 50) * 5)),
                foreground=self.get_font_color((self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                command=self.stoplistenmode)

        if permit_web == "yes" and frequency != "" and 5 < float(frequency) < 30000:
            try:
                self.menu.add_command(
                    label="Open \"" + str(host).rsplit("$", 14)[0] + "/f=" + str(frequency) + "iqz8\" in browser",
                    state=NORMAL, background=(self.color_variant(colorline[0], (int(temp_snr_avg) - 50) * 5)),
                    foreground=self.get_font_color((self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))),
                    command=self.openinbrowser)
                if float(frequency) <= 2000:
                    font_snr1 = 'TkFixedFont 8 bold'
                elif 2001 < float(frequency) <= 10000:
                    font_snr2 = 'TkFixedFont 8 bold'
                elif 10001 < float(frequency) <= 20000:
                    font_snr3 = 'TkFixedFont 8 bold'
                elif 20001 < float(frequency) <= 30000:
                    font_snr4 = 'TkFixedFont 8 bold'
            except:
                pass

        self.menu.add_command(
            label=str(host.rsplit("$", 14)[2]) + " | " + str(host.rsplit("$", 14)[3]).replace("_",
                                                                                              " ") + " | USERS " + str(
                host.rsplit("$", 14)[4]) + "/" + str(host.rsplit("$", 14)[5]) + " | GPS " + str(
                host.rsplit("$", 14)[6]) + " fix/min", state=NORMAL,
            background=(self.color_variant(colorline[0], (int(temp_snr_avg) - 50) * 5)),
            foreground=self.get_font_color((self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))), command=None)
        try:
            if host.rsplit("$", 14)[11] != '0':
                self.menu.add_separator()
                self.menu.add_command(label="AVG SNR on 0-30 MHz: " + str(temp_snr_avg) + " dB - AVG Noise: " + str(
                    temp_noise_avg) + " dBm (S" + str(self.convert_dbm_to_smeter(int(temp_noise_avg))) + ")",
                                      background=(self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5)),
                                      foreground=self.get_font_color(
                                          (self.color_variant("#FFFF00", (int(temp_snr_avg) - 50) * 5))), command=None)
                self.menu.add_separator()
                self.menu.add_command(
                    label="AVG SNR on 0-2 MHz: " + host.rsplit("$", 14)[7] + " dB - AVG Noise: " + host.rsplit("$", 14)[
                        11] + " dBm (S" + str(self.convert_dbm_to_smeter(int(host.rsplit("$", 14)[11]))) + ")",
                    background=(self.color_variant("#FFFF00", (int(host.rsplit("$", 14)[7]) - 50) * 5)),
                    foreground=self.get_font_color(
                        (self.color_variant("#FFFF00", (int(host.rsplit("$", 14)[7]) - 50) * 5))), font=font_snr1,
                    command=None)
                self.menu.add_command(
                    label="AVG SNR on 2-10 MHz: " + host.rsplit("$", 14)[8] + " dB - AVG Noise: " +
                          host.rsplit("$", 14)[
                              12] + " dBm (S" + str(self.convert_dbm_to_smeter(int(host.rsplit("$", 14)[12]))) + ")",
                    background=(self.color_variant("#FFFF00", (int(host.rsplit("$", 14)[8]) - 50) * 5)),
                    foreground=self.get_font_color(
                        (self.color_variant("#FFFF00", (int(host.rsplit("$", 14)[8]) - 50) * 5))), font=font_snr2,
                    command=None)
                self.menu.add_command(
                    label="AVG SNR on 10-20 MHz: " + host.rsplit("$", 14)[9] + " dB - AVG Noise: " +
                          host.rsplit("$", 14)[
                              13] + " dBm (S" + str(self.convert_dbm_to_smeter(int(host.rsplit("$", 14)[13]))) + ")",
                    background=(self.color_variant("#FFFF00", (int(host.rsplit("$", 14)[9]) - 50) * 5)),
                    foreground=self.get_font_color(
                        (self.color_variant("#FFFF00", (int(host.rsplit("$", 14)[9]) - 50) * 5))), font=font_snr3,
                    command=None)
                self.menu.add_command(
                    label="AVG SNR on 20-30 MHz: " + host.rsplit("$", 14)[10] + " dB - AVG Noise: " +
                          host.rsplit("$", 14)[
                              14] + " dBm (S" + str(self.convert_dbm_to_smeter(int(host.rsplit("$", 14)[14]))) + ")",
                    background=(self.color_variant("#FFFF00", (int(host.rsplit("$", 14)[10]) - 50) * 5)),
                    foreground=self.get_font_color(
                        (self.color_variant("#FFFF00", (int(host.rsplit("$", 14)[10]) - 50) * 5))), font=font_snr4,
                    command=None)
            else:
                self.menu.add_separator()
        except:
            pass
        if host.rsplit('$', 14)[1] in white:  # if node is a favorite
            self.menu.add_command(label="remove from favorites", command=self.remfavorite)
        elif host.rsplit('$', 14)[1] not in black:
            self.menu.add_command(label="add to favorites", command=self.addfavorite)
        if host.rsplit('$', 14)[1] in black:  # if node is blacklisted
            self.menu.add_command(label="remove from blacklist", command=self.remblacklist)
        elif host.rsplit('$', 14)[1] not in white:
            self.menu.add_command(label="add to blacklist", command=self.addblacklist)

        # self.menu.add_command(label="check SNR", state=DISABLED, command=self.displaySNR)  # for next devel
        # if snrcheck == True:
        #     print "SNR requested on " + str(self.canvas.gettags(self.canvas.find_withtag(CURRENT))[0].rsplit(':')[0])
        #     print snrfreq
        #     snrhost = str(self.canvas.gettags(self.canvas.find_withtag(CURRENT))[0].rsplit(':')[0])
        #     SnrProcessing(self).start()
        #     app.title("Checking SNR for" + str(snrhost) + ". Please wait")

        self.menu.post(event.x_root, event.y_root)

    def get_font_color(self, ff):  # adapting the font color regarding background luminosity
        # stackoverflow.com/questions/946544/good-text-foreground-color-for-a-given-background-color/946734#946734
        rgb_hex = [ff[x:x + 2] for x in [1, 3, 5]]
        if int(rgb_hex[0], 16) * 0.299 + int(rgb_hex[1], 16) * 0.587 + int(rgb_hex[2], 16) * 0.114 > 186:
            return "#000000"
        else:
            return "#FFFFFF"
        # if (red*0.299 + green*0.587 + blue*0.114) > 186 use #000000 else use #ffffff
        pass

    def convert_dbm_to_smeter(self, dbm):
        dBm_values = [-121, -115, -109, -103, -97, -91, -85, -79, -73, -63, -53, -43, -33, -23, -13, -3]
        if dbm != 0:
            return next(x[0] for x in enumerate(dBm_values) if x[1] > dbm)
        else:
            return "--"

    def color_variant(self, hex_color, brightness_offset=1):
        # source : https://chase-seibert.github.io/blog/2011/07/29/python-calculate-lighterdarker-rgb-colors.html
        rgb_hex = [hex_color[x:x + 2] for x in [1, 3, 5]]
        new_rgb_int = [int(hex_value, 16) + brightness_offset for hex_value in rgb_hex]
        new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int]
        return "#" + "".join(["0" + hex(i)[2:] if len(hex(i)[2:]) < 2 else hex(i)[2:] for i in new_rgb_int])

    def addfavorite(self):
        global white, black
        ReadConfigFile().read_cfg()
        if host.rsplit('$', 14)[1] in white:
            tkMessageBox.showinfo(title="  ¯\_(ツ)_/¯ ",
                                  message=str(host.rsplit(':')[0]) + " is already in the favorite list !")
        else:
            os.remove('directKiwi.cfg')
            with open('directKiwi.cfg', "w") as u:
                u.write("This is " + VERSION + " config file\n")
                u.write(
                    "This file should be generated by directKiwi software only, in case something went wrong you can find a sample here: https://raw.githubusercontent.com/llinkz/directKiwi/master/directKiwi.cfg\n")
                u.write("# Default map geometry \n%s,%s,%s,%s" % (dx0, dy0, dx1, dy1))
                u.write("# Default map picture \n%s\n" % dmap)
                u.write(
                    "# Default map filter (0= All  1= Standard+Favorites  2= Favorites  3= Blacklisted) \n%s\n" % (
                        mapfl))
                if white[0] == "":
                    u.write("# Whitelist \n%s\n" % host.rsplit('$', 14)[1])
                    u.write("# Blacklist \n%s\n" % ','.join(black))
                else:
                    white.append(host.rsplit('$', 14)[1])
                    u.write("# Whitelist \n%s\n" % ','.join(white))
                    u.write("# Blacklist \n%s\n" % ','.join(black))
                u.write("# Default Colors (standard,favorites,blacklisted,known) \n%s\n" % ','.join(colorline))
                u.write(
                    "# Default Audio Settings (LP,HP,AGC/MGC,HANG,GAIN,THRESHOLD,SLOPE,DECAY) \n%s,%s,%s,%s,%s,%s,%s,%s" % (
                        lp_cut, hp_cut, autoagcactive, hang, managcgain, threshold, slope, decay))
            u.close()
            tkMessageBox.showinfo(title=" ",
                                  message=str(host.rsplit(':')[0]) + " has been added to the favorite list !")
            Restart().run()

    def remfavorite(self):
        global white, black, newwhite
        newwhite = []
        ReadConfigFile().read_cfg()
        for f in white:
            if f != host.rsplit('$', 14)[1]:
                newwhite.append(f)
        os.remove('directKiwi.cfg')
        with open('directKiwi.cfg', "w") as u:
            u.write("This is " + VERSION + " config file\n")
            u.write(
                "This file should be generated by directKiwi software only, in case something went wrong you can find a sample here: https://raw.githubusercontent.com/llinkz/directKiwi/master/directKiwi.cfg\n")
            u.write("# Default map geometry \n%s,%s,%s,%s" % (dx0, dy0, dx1, dy1))
            u.write("# Default map picture \n%s\n" % (dmap))
            u.write(
                "# Default map filter (0= All  1= Standard+Favorites  2= Favorites  3= Blacklisted) \n%s\n" % (
                    mapfl))
            u.write("# Whitelist \n%s\n" % ','.join(newwhite))
            u.write("# Blacklist \n%s\n" % ','.join(black))
            u.write("# Default Colors (standard,favorites,blacklisted,known) \n%s\n" % ','.join(colorline))
            u.write(
                "# Default Audio Settings (LP,HP,AGC/MGC,HANG,GAIN,THRESHOLD,SLOPE,DECAY) \n%s,%s,%s,%s,%s,%s,%s,%s" % (
                    lp_cut, hp_cut, autoagcactive, hang, managcgain, threshold, slope, decay))
        u.close()
        tkMessageBox.showinfo(title=" ",
                              message=str(host.rsplit(':')[0]) + " has been removed from the favorites list !")
        Restart().run()

    def addblacklist(self):
        ReadConfigFile().read_cfg()
        if host.rsplit('$', 14)[1] in black:
            tkMessageBox.showinfo(title="  ¯\_(ツ)_/¯ ",
                                  message=str(host.rsplit(':')[0]) + " is already blacklisted !")
        else:
            os.remove('directKiwi.cfg')
            with open('directKiwi.cfg', "w") as u:
                u.write("This is " + VERSION + " config file\n")
                u.write(
                    "This file should be generated by directKiwi software only, in case something went wrong you can find a sample here: https://raw.githubusercontent.com/llinkz/directKiwi/master/directKiwi.cfg\n")
                u.write("# Default map geometry \n%s,%s,%s,%s" % (dx0, dy0, dx1, dy1))
                u.write("# Default map picture \n%s\n" % dmap)
                u.write(
                    "# Default map filter (0= All  1= Standard+Favorites  2= Favorites  3= Blacklisted) \n%s\n" % (
                        mapfl))
                if black[0] == "":
                    u.write("# Whitelist \n%s\n" % ','.join(white))
                    u.write("# Blacklist \n%s\n" % host.rsplit('$', 14)[1])
                else:
                    black.append(host.rsplit('$', 14)[1])
                    u.write("# Whitelist \n%s\n" % ','.join(white))
                    u.write("# Blacklist \n%s\n" % ','.join(black))
                u.write("# Default Colors (standard,favorites,blacklisted,known) \n%s\n" % ','.join(colorline))
                u.write(
                    "# Default Audio Settings (LP,HP,AGC/MGC,HANG,GAIN,THRESHOLD,SLOPE,DECAY) \n%s,%s,%s,%s,%s,%s,%s,%s" % (
                        lp_cut, hp_cut, autoagcactive, hang, managcgain, threshold, slope, decay))
            u.close()
            tkMessageBox.showinfo(title=" ",
                                  message=str(host.rsplit(':')[0]) + " has been added to the blacklist !")
            Restart().run()

    def remblacklist(self):
        global white, black, newblack
        newblack = []
        ReadConfigFile().read_cfg()
        for f in black:
            if f != host.rsplit('$', 14)[1]:
                newblack.append(f)
        os.remove('directKiwi.cfg')
        with open('directKiwi.cfg', "w") as u:
            u.write("This is " + VERSION + " config file\n")
            u.write(
                "This file should be generated by directKiwi software only, in case something went wrong you can find a sample here: https://raw.githubusercontent.com/llinkz/directKiwi/master/directKiwi.cfg\n")
            u.write("# Default map geometry \n%s,%s,%s,%s" % (dx0, dy0, dx1, dy1))
            u.write("# Default map picture \n%s\n" % dmap)
            u.write(
                "# Default map filter (0= All  1= Standard+Favorites  2= Favorites  3= Blacklisted) \n%s\n" % (
                    mapfl))
            u.write("# Whitelist \n%s\n" % ','.join(white))
            u.write("# Blacklist \n%s\n" % ','.join(newblack))
            u.write("# Default Colors (standard,favorites,blacklisted,known) \n%s\n" % ','.join(colorline))
            u.write(
                "# Default Audio Settings (LP,HP,AGC/MGC,HANG,GAIN,THRESHOLD,SLOPE,DECAY) \n%s,%s,%s,%s,%s,%s,%s,%s" % (
                    lp_cut, hp_cut, autoagcactive, hang, managcgain, threshold, slope, decay))
        u.close()
        tkMessageBox.showinfo(title=" ",
                              message=str(host.rsplit(':')[0]) + " has been removed from the blacklist !")
        Restart().run()

    def openinbrowser(self):
        if frequency != 10000:
            url = "http://" + str(host).rsplit("$", 14)[0] + "/?f=" + str(frequency) + "iqz8"
            webbrowser.open_new(url)
        else:
            url = "http://" + str(host).rsplit("$", 14)[0]
            webbrowser.open_new(url)

    def listenmode(self, d):
        global server_host, server_port, frequency, listenmode, kiwisdrclient_pid, dd
        server_host = str(host).rsplit("$", 14)[0].rsplit(":", 2)[0]
        server_port = str(host).rsplit("$", 14)[0].rsplit(":", 2)[1]
        frequency = app.window2.Entry1.get()
        dd = d
        if listenmode == "0":
            StartKiwiSDRclient(self).start()
            app.title(str(VERSION) + " - [ " + server_host + " / " + frequency + " kHz / " + str(dd).upper() + " ]")
        else:
            os.kill(kiwisdrclient_pid, signal.SIGTERM)
            app.title(VERSION)
            StartKiwiSDRclient(self).start()
            app.title(str(VERSION) + " - [ " + server_host + " / " + frequency + " kHz / " + str(dd).upper() + " ]")

    def stoplistenmode(self):
        global listenmode, kiwisdrclient_pid
        os.kill(kiwisdrclient_pid, signal.SIGTERM)
        listenmode = "0"
        app.window2.writelog("Stopping Listen mode")
        app.title(VERSION)
        app.window2.label3.configure(text=" --- dBm")
        app.window2.TProgressbar1.configure(value='0')

    def scroll_y(self, *args, **kwargs):
        self.canvas.yview(*args, **kwargs)  # scroll vertically
        self.show_image()  # redraw the image

    def scroll_x(self, *args, **kwargs):
        self.canvas.xview(*args, **kwargs)  # scroll horizontally
        self.show_image()  # redraw the image

    def move_from(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def move_to(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.show_image()  # redraw the image

    def wheel(self, event):
        global bbox
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        bbox = self.canvas.bbox(self.container)  # get image area
        if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]:
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
        self.canvas.scale('all', x, y, scale, scale)  # rescale all canvas objects
        self.show_image()

    def show_image(self, event=None):
        global bbox1, bbox2, x1, x2, y1, y2
        bbox1 = self.canvas.bbox(self.container)  # get image area
        # Remove 1 pixel shift at the sides of the bbox1
        bbox1 = (bbox1[0] + 1, bbox1[1] + 1, bbox1[2] - 1, bbox1[3] - 1)
        bbox2 = (self.canvas.canvasx(0),  # get visible area of the canvas
                 self.canvas.canvasy(0),
                 self.canvas.canvasx(self.canvas.winfo_width()),
                 self.canvas.canvasy(self.canvas.winfo_height()))
        bbox = [min(bbox1[0], bbox2[0]), min(bbox1[1], bbox2[1]),  # get scroll region box
                max(bbox1[2], bbox2[2]), max(bbox1[3], bbox2[3])]
        if bbox[0] == bbox2[0] and bbox[2] == bbox2[2]:  # whole image in the visible area
            bbox[0] = bbox1[0]
            bbox[2] = bbox1[2]
        if bbox[1] == bbox2[1] and bbox[3] == bbox2[3]:  # whole image in the visible area
            bbox[1] = bbox1[1]
            bbox[3] = bbox1[3]
        self.canvas.configure(scrollregion=bbox)  # set scroll region
        x1 = max(bbox2[0] - bbox1[0], 0)  # get coordinates (x1,y1,x2,y2) of the image tile
        y1 = max(bbox2[1] - bbox1[1], 0)
        x2 = min(bbox2[2], bbox1[2]) - bbox1[0]
        y2 = min(bbox2[3], bbox1[3]) - bbox1[1]
        if int(x2 - x1) > 0 and int(y2 - y1) > 0:  # show image if it in the visible area
            x = min(int(x2 / self.imscale), self.width)  # sometimes it is larger on 1 pixel...
            y = min(int(y2 / self.imscale), self.height)  # ...and sometimes not
            image = self.image.crop((int(x1 / self.imscale), int(y1 / self.imscale), x, y))
            imagetk = ImageTk.PhotoImage(image.resize((int(x2 - x1), int(y2 - y1))))
            imageid = self.canvas.create_image(max(bbox2[0], bbox1[0]), max(bbox2[1], bbox1[1]),
                                               anchor='nw', image=imagetk)
            self.canvas.lower(imageid)  # set image into background
            self.canvas.imagetk = imagetk  # keep an extra reference to prevent garbage-collection


class MainWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent)
        # self.parent = parent
        self.member1 = ZoomAdvanced(parent)
        if os.path.isfile('directKiwi_server_list.db') is not True:
            tkMessageBox.showinfo(title="  ¯\_(ツ)_/¯ ", message="oops no node db found, Click OK to run an update now")
            CheckUpdate().run()
        global frequency
        global line, i, bgc, fgc, dfgc, lpcut, hpcut, currentbw
        global latmin, latmax, lonmin, lonmax, bbox1
        frequency = DoubleVar(self, 10000.0)
        bgc = '#d9d9d9'  # GUI background color
        bgc = "grey"
        fgc = '#000000'  # GUI foreground color
        dfgc = '#a3a3a3'  # GUI (disabled) foreground color
        self.label0 = Label(parent)
        self.label0.place(relx=0, rely=0.76, relheight=0.3, relwidth=1)
        self.label0.configure(bg=bgc, fg=fgc, width=214)
        self.label1 = Label(parent)
        self.label1.place(relx=0, rely=0, relheight=0.05, relwidth=1)
        self.label1.configure(bg=bgc, fg=fgc, width=214)
        self.label05 = Label(parent)
        self.label05.place(relx=0.6, rely=0.766, relheight=0.03, relwidth=0.38)
        self.label05.configure(bg="darkgrey", fg=fgc, width=214)
        self.label00 = Label(parent)
        self.label00.place(relx=0.61, rely=0.77, height=14, width=75)
        self.label00.configure(bg="darkgrey", font="TkFixedFont 7", anchor="w", fg="black", text="Map legend :")
        self.label01 = Label(parent)
        self.label01.place(relx=0.675, rely=0.77, height=14, width=75)
        self.label01.configure(bg="darkgrey", font="TkFixedFont 7", anchor="w", fg=colorline[0], text="█ Standard")
        self.label02 = Label(parent)
        self.label02.place(relx=0.75, rely=0.77, height=14, width=75)
        self.label02.configure(bg="darkgrey", font="TkFixedFont 7", anchor="w", fg=colorline[1], text="█ Favorite")
        self.label03 = Label(parent)
        self.label03.place(relx=0.825, rely=0.77, height=14, width=75)
        self.label03.configure(bg="darkgrey", font="TkFixedFont 7", anchor="w", fg=colorline[2], text="█ Blacklisted")
        self.label04 = Label(parent)
        self.label04.place(relx=0.905, rely=0.77, height=14, width=75)
        self.label04.configure(bg="darkgrey", font="TkFixedFont 7", anchor="w", fg="#001E00", text="█ no SNR data")
        self.label1 = Label(parent)
        self.label1.place(relx=0.605, rely=0.95)
        self.label1.configure(bg=bgc, font="TkFixedFont", fg=fgc, text="Freq:")
        self.label2 = Label(parent)
        self.label2.place(relx=0.73, rely=0.95)
        self.label2.configure(bg=bgc, font="TkFixedFont", fg=fgc, text="kHz")
        self.label3 = Label(parent)
        self.label3.place(relx=0.93, y=0)
        self.label3.configure(bg=bgc, font="TkFixedFont", fg=fgc, text=" --- dBm")
        self.Entry1 = Entry(parent, textvariable=frequency)  # Frequency box
        self.Entry1.place(relx=0.65, rely=0.948, height=23, width=80)
        self.Entry1.configure(bg="white", disabledforeground=dfgc, font="TkFixedFont", fg=fgc,
                              insertbackground=fgc, width=214)
        self.Entry1.bind('<Control-a>', self.ctrla)
        self.Button5 = Button(parent)  # Restart GUI button
        self.Button5.place(relx=0.828, rely=0.95, height=24, width=80)
        self.Button5.configure(activebackground=bgc, activeforeground=fgc, bg="red", disabledforeground=dfgc,
                               fg=fgc, highlightbackground=bgc, highlightcolor=fgc, pady="0",
                               text="Restart GUI", command=Restart().run, state="normal")
        self.Button3 = Button(parent)  # Update button
        self.Button3.place(relx=0.915, rely=0.95, height=24, width=80)
        self.Button3.configure(activebackground=bgc, activeforeground=fgc, bg="orange", disabledforeground=dfgc,
                               fg=fgc, highlightbackground=bgc, highlightcolor=fgc, pady="0",
                               text="update map", command=self.runupdate, state="normal")
        self.Text2 = Text(parent)  # Console window
        self.Text2.place(relx=0.001, rely=0.768, relheight=0.23, relwidth=0.573)
        self.Text2.configure(bg="black", font="TkTextFont", fg="green", highlightbackground=bgc,
                             highlightcolor=fgc, insertbackground=fgc, selectbackground="#c4c4c4",
                             selectforeground=fgc, undo="1", width=970, wrap="word")
        vsb2 = Scrollbar(parent, orient="vertical", command=self.Text2.yview)  # adding scrollbar to console
        vsb2.place(relx=0.575, rely=0.769, relheight=0.228, width=18)
        self.Text2.configure(yscrollcommand=vsb2.set)
        self.TProgressbar1 = ttk.Progressbar(parent)  # s-meter
        self.TProgressbar1.place(x=0, y=0, height=20, relwidth=0.93)
        self.TProgressbar1.configure(length="970", maximum="110", value='0')
        # s-meter scale and placement
        smetertext = ['', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', '+10', '+20', '+30', '+40', '+50', '']
        smeterplaces = ['0', '0.01', '0.046', '0.097', '0.151', '0.205', '0.256', '0.310', '0.361', '0.415', '0.496',
                        '0.585', '0.669', '0.7565', '0.8455', '0.9315']
        s = 0
        while s < len(smetertext):
            self.label = Label(parent)
            self.label.place(relx=smeterplaces[s], y=20, height=20, relheight=0.0, relwidth=0.97)
            self.label.configure(background="grey", foreground=fgc, relief="flat", anchor='w', text=smetertext[s])
            s += 1
        self.Scale2 = Scale(parent, from_=0, to=6000)  # low pass filter scale
        self.Scale2.place(relx=0.6, rely=0.8, relwidth=0.4, height=40)
        self.Scale2.set(lp_cut)
        self.Scale2.configure(activebackground=bgc, background=bgc, font="TkTextFont", foreground=fgc,
                              highlightbackground=bgc, highlightcolor=fgc, length="970", orient="horizontal",
                              showvalue="0", troughcolor="grey", resolution=10,
                              label="Low Pass Filter (0Hz)", command=self.changelpvalue)
        self.Scale3 = Scale(parent, from_=0, to=6000)  # high pass filter scale
        self.Scale3.place(relx=0.6, rely=0.87, relwidth=0.4, height=40)
        self.Scale3.set(hp_cut)
        self.Scale3.configure(activebackground=bgc, background=bgc, font="TkTextFont", foreground=fgc,
                              highlightbackground=bgc, highlightcolor=fgc, length="970", orient="horizontal",
                              showvalue="0", troughcolor="grey", resolution=10,
                              label="High Pass Filter (3600Hz)", command=self.changehpvalue)
        self.writelog("This is " + VERSION + ", a GUI written for python 2.7 / Tk")
        self.writelog("Thanks to Pierre (linkfanel) for his listing of available KiwiSDR nodes")
        self.writelog("Thanks to Marco (IS0KYB) for his SNR measurements listing of the KiwiSDR network")
        self.writelog("There are [" + str(nodecount) + "] KiwiSDRs in the db. Have fun !")
        self.writelog("Low Pass Cut Filter [" + str(lp_cut) + "Hz] - High Pass Cut Filter [" + str(hp_cut) + "Hz]")
        if autoagcactive == '1':
            self.writelog("AGC is [ON]")
        elif autoagcactive == '0' and hang == '0':
            self.writelog("MGC is [ON] - [Gain " + str(managcgain) + "dB] - Hang [OFF] - Threshold [" + str(
                threshold) + "dB] - Slope [" + str(slope) + "dB] - Decay [" + str(decay).replace("\n", "") + "ms]")
        else:
            self.writelog("MGC is [ON] - Gain [" + str(managcgain) + "dB] - Hang [ON] - Threshold [" + str(
                threshold) + "dB] - Slope [" + str(slope) + "dB] - Decay [" + str(decay).replace("\n", "") + "ms]")
        # -------------------------------------------------LOGGING AND MENUS--------------------------------------------
        menubar = Menu(self)
        parent.config(menu=menubar)
        filemenu = Menu(menubar, tearoff=0)  # Audio settings
        filemenu2 = Menu(menubar, tearoff=0)  # Map Settings
        filemenu3 = Menu(menubar, tearoff=0)  # About
        menubar.add_cascade(label="Audio Settings", menu=filemenu)
        menubar.add_cascade(label="Map Settings", menu=filemenu2)
        submenu2 = Menu(filemenu, tearoff=0)
        submenu21 = Menu(filemenu, tearoff=0)
        submenu21.add_command(label="Low pass filter", command=self.defaultlowpass)
        submenu21.add_command(label="High pass filter", command=self.defaulthighpass)
        submenu2.add_cascade(label='Default', menu=submenu21, underline=0)
        submenu4 = Menu(filemenu, tearoff=0)
        submenu41 = Menu(filemenu, tearoff=0)
        submenu42 = Menu(filemenu, tearoff=0)
        submenu43 = Menu(filemenu, tearoff=0)
        submenu42.add_command(label="On", command=lambda *args: self.default_agc_hang(1))
        submenu42.add_command(label="Off", command=lambda *args: self.default_agc_hang(0))
        submenu43.add_command(label="AGC", command=lambda *args: self.default_agc(1))
        submenu43.add_command(label="MGC", command=lambda *args: self.default_agc(0))
        submenu41.add_cascade(label="AGC/MGC", menu=submenu43, underline=0)
        submenu41.add_cascade(label='Hang', menu=submenu42, underline=0)
        submenu41.add_command(label="Manual Gain", command=lambda *args: self.default_agc_gain())
        submenu41.add_command(label="Threshold", command=lambda *args: self.default_agc_threshold())
        submenu41.add_command(label="Slope", command=lambda *args: self.default_agc_slope())
        submenu41.add_command(label="Decay", command=lambda *args: self.default_agc_decay())
        submenu4.add_cascade(label='Default', menu=submenu41, underline=0)
        filemenu.add_cascade(label='Bandwidth', menu=submenu2, underline=0)
        filemenu.add_cascade(label='Gain control', menu=submenu4, underline=0)
        submenu4 = Menu(filemenu2, tearoff=0)
        submenu5 = Menu(filemenu2, tearoff=0)
        submenu6 = Menu(filemenu2, tearoff=0)
        filemenu2.add_cascade(label='Default map', menu=submenu4, underline=0)
        submenu4.add_command(label="Browse maps folder", command=self.choose_map)
        filemenu2.add_cascade(label='Map Filters', menu=submenu5, underline=0)
        submenu5.add_command(label="Display All nodes", command=lambda *args: self.setmapfilter('0'))
        submenu5.add_command(label="Display Standard + Favorites", command=lambda *args: self.setmapfilter('1'))
        submenu5.add_command(label="Display Favorites", command=lambda *args: self.setmapfilter('2'))
        submenu5.add_command(label="Display Blacklisted", command=lambda *args: self.setmapfilter('3'))
        filemenu2.add_cascade(label='Set Colors', menu=submenu6, underline=0)
        submenu6.add_command(label="Standard node color", command=lambda *args: self.color_change(0))
        submenu6.add_command(label="Favorite node color", command=lambda *args: self.color_change(1))
        submenu6.add_command(label="Blacklisted node color", command=lambda *args: self.color_change(2))
        menubar.add_cascade(label="?", menu=filemenu3)
        filemenu3.add_command(label="Help", command=self.help)
        filemenu3.add_command(label="About", command=self.about)
        filemenu3.add_command(label="Check for Update Now...", command=self.checkversion)
        self.Entry1.delete(0, 'end')
        self.checkversion()

    def defaultlowpass(self):  # low pass filter default menu
        global lp_cut, topL
        topL = Tk()
        topL.geometry("280x50+50+50")
        topL.title('Default low pass filter (in Hz)')
        low_pass_slider = Scale(topL, from_=0, to=6000)
        low_pass_slider.place(x=10, y=0, width=200, height=100)
        low_pass_slider.configure(orient="horizontal", showvalue="1", resolution=100, label="")
        low_pass_slider.set(lp_cut)
        low_pass_button = Button(topL, command=lambda *args: self.setdefaultlowpass(low_pass_slider.get()))
        low_pass_button.place(x=220, y=20, height=20)
        low_pass_button.configure(text="Save")

    @staticmethod
    def setdefaultlowpass(lowvalue):
        global defaultlowpassvalue, topL
        defaultlowpassvalue = lowvalue
        app.window2.writelog("Low Pass filter set to " + str(lowvalue) + "Hz")
        SaveConfigFile().save_cfg("lp_cut", lowvalue)
        topL.destroy()

    def defaulthighpass(self):  # high pass filter default menu
        global hp_cut, topH
        topH = Tk()
        topH.geometry("280x50+50+50")
        topH.title('Default high pass filter (in Hz)')
        high_pass_slider = Scale(topH, from_=0, to=6000)
        high_pass_slider.place(x=10, y=0, width=200, height=100)
        high_pass_slider.configure(orient="horizontal", showvalue="1", resolution=100, label="")
        high_pass_slider.set(hp_cut)
        high_pass_button = Button(topH, command=lambda *args: self.setdefaulthighpass(high_pass_slider.get()))
        high_pass_button.place(x=220, y=20, height=20)
        high_pass_button.configure(text="Save")

    @staticmethod
    def setdefaulthighpass(highvalue):
        global defaulthighpassvalue, topH
        defaulthighpassvalue = highvalue
        app.window2.writelog("High Pass filter set to " + str(highvalue) + "Hz")
        SaveConfigFile().save_cfg("hp_cut", highvalue)
        topH.destroy()

    @staticmethod
    def default_agc(agcset):
        global autoagcactive
        autoagcactive = agcset
        SaveConfigFile().save_cfg("autoagcactive", agcset)

    @staticmethod
    def default_agc_hang(agchang):
        global hang
        hang = agchang
        SaveConfigFile().save_cfg("hang", agchang)

    def default_agc_gain(self):
        global managcgain, topG
        topG = Tk()
        topG.geometry("280x50+50+50")
        topG.title('Default gain (in MGC mode)')
        agc_gain_slider = Scale(topG, from_=0, to=120)
        agc_gain_slider.place(x=10, y=0, width=200, height=100)
        agc_gain_slider.configure(orient="horizontal", showvalue="1", resolution=1, label="")
        agc_gain_slider.set(managcgain)
        agc_gain_button = Button(topG, command=lambda *args: self.set_default_agc_gain(agc_gain_slider.get()))
        agc_gain_button.place(x=220, y=20, height=20)
        agc_gain_button.configure(text="Save")

    @staticmethod
    def set_default_agc_gain(gainvalue):
        global managcgain, topG
        managcgain = gainvalue
        app.window2.writelog("Audio Gain set to " + str(gainvalue))
        SaveConfigFile().save_cfg("managcgain", gainvalue)
        topG.destroy()

    def default_agc_threshold(self):
        global threshold, topT
        topT = Tk()
        topT.geometry("280x50+50+50")
        threshold_slider = Scale(topT, from_=-130, to=0)
        threshold_slider.place(x=10, y=0, width=200, height=100)
        threshold_slider.configure(orient="horizontal", showvalue="1", resolution=1, label="")
        threshold_slider.set(threshold)
        threshold_button = Button(topT, command=lambda *args: self.set_default_agc_thres(threshold_slider.get()))
        threshold_button.place(x=220, y=20, height=20)
        threshold_button.configure(text="Save")

    @staticmethod
    def set_default_agc_thres(thresvalue):
        global threshold, topT
        threshold = thresvalue
        app.window2.writelog("Audio Gain Threshold set to " + str(thresvalue))
        SaveConfigFile().save_cfg("threshold", thresvalue)
        topT.destroy()

    def default_agc_slope(self):
        global slope, topS
        topS = Tk()
        topS.geometry("280x50+50+50")
        topS.title('Default slope (in AGC mode)')
        slope_slider = Scale(topS, from_=0, to=10)
        slope_slider.place(x=10, y=0, width=200, height=100)
        slope_slider.configure(orient="horizontal", showvalue="1", resolution=1, label="")
        slope_slider.set(slope)
        slope_button = Button(topS, command=lambda *args: self.set_default_agc_slope(slope_slider.get()))
        slope_button.place(x=220, y=20, height=20)
        slope_button.configure(text="Save")

    @staticmethod
    def set_default_agc_slope(slopevalue):
        global slope, topS
        slope = slopevalue
        app.window2.writelog("Audio Gain Slope set to " + str(slopevalue))
        SaveConfigFile().save_cfg("slope", slopevalue)
        topS.destroy()

    def default_agc_decay(self):
        global decay, topD
        topD = Tk()
        topD.geometry("280x50+50+50")
        decay_slider = Scale(topD, from_=20, to=5000)
        decay_slider.place(x=10, y=0, width=200, height=100)
        decay_slider.configure(orient="horizontal", showvalue="1", resolution=10, label="")
        decay_slider.set(decay)
        decay_button = Button(topD, command=lambda *args: self.set_default_agc_decay(decay_slider.get()))
        decay_button.place(x=220, y=20, height=20)
        decay_button.configure(text="Save")

    @staticmethod
    def set_default_agc_decay(decayvalue):
        global decay, topD
        decay = decayvalue
        app.window2.writelog("Audio Gain Decay to " + str(decayvalue))
        SaveConfigFile().save_cfg("decay", decayvalue)
        topD.destroy()

    def changelpvalue(self, lpvalue):
        global lp_cut
        self.Scale2.configure(label="Low Pass Filter (" + str(lpvalue) + "Hz)")
        if self.Scale2.get() >= self.Scale3.get():
            self.Scale3.set(self.Scale2.get() + 10)
            lp_cut = self.Scale2.get()
            self.bandwidth = int(self.Scale3.get()) - int(self.Scale2.get())
        else:
            self.bandwidth = int(self.Scale3.get()) - int(self.Scale2.get())
            lp_cut = self.Scale2.get()
        return lp_cut

    def changehpvalue(self, hpvalue):
        global hp_cut
        self.Scale3.configure(label="High Pass Filter (" + str(hpvalue) + "Hz)")
        if self.Scale3.get() <= self.Scale2.get():
            self.Scale2.set(self.Scale3.get() - 10)  # self.adaptlp(lpvalue=self.Scale3.get() - 10)
            self.bandwidth = int(self.Scale3.get()) - int(self.Scale2.get())
            hp_cut = self.Scale3.get()
        else:
            self.bandwidth = int(self.Scale3.get()) - int(self.Scale2.get())
            hp_cut = self.Scale3.get()
        return hp_cut

    # @staticmethod
    def ctrla(self, event):
        event.widget.select_range(0, 'end')
        event.widget.icursor('end')
        return 'break'

    def writelog(self, msg):  # the main console log text feed
        self.Text2.insert('end -1 lines', "[" + str(time.strftime('%H:%M.%S', time.gmtime())) + "] - " + msg + "\n")
        time.sleep(0.01)
        self.Text2.see('end')

    @staticmethod
    def help():
        master = Tk()
        w = Message(master, text="""
    1/ Enter a frequency
    2/ Click on a node and choose Listen, then Mode
    To disconnect click any node and choose Stop Listen
    
    You can also open a web browser by choosing Open entry
    
    You can zoom the map using the mouse wheel
    """, width=1000, font="TkFixedFont 8", bg="white", anchor="center")
        w.pack()

    @staticmethod
    def about():  # About menu
        master = Tk()
        w = Message(master, text="""
    Welcome to """ + VERSION + """

    The World map is static, click UPDATE button to get an updated node list
    KiwiSDR node informations are retrieved in real time when node square icon is clicked on the map

    Thanks to Pierre Ynard (linkfanel) for the KiwiSDR network node listing used as source for GUI map update
    Thanks to Marco Cogoni (IS0KYB) for the KiwiSDR network SNR measurements listing used as source for GUI map update
    And.. Thanks to all KiwiSDR hosters...

    linkz 

    feedback, features request or help : contact me at ounaid at gmail dot com or IRC freenode #wunclub / #priyom
    """, width=1000, font="TkFixedFont 8", bg="white", anchor="center")
        w.pack()

    # @staticmethod
    def setmapfilter(self, mapfl):
        ReadConfigFile().read_cfg()
        SaveConfigFile().save_cfg("mapfl", mapfl)
        Restart().run()

    # @staticmethod
    def color_change(self, value):  # node color choices
        global colorline
        color_n = askcolor()
        color_n = color_n[1]
        ReadConfigFile().read_cfg()
        if color_n:
            if value == 0:
                colorline = color_n + "," + colorline[1] + "," + colorline[2] + "," + colorline[3]
            elif value == 1:
                colorline = colorline[0] + "," + color_n + "," + colorline[2] + "," + colorline[3]
            elif value == 2:
                colorline = colorline[0] + "," + colorline[1] + "," + color_n + "," + colorline[3]
            elif value == 3:
                colorline = colorline[0] + "," + colorline[1] + "," + colorline[2] + "," + color_n
            SaveConfigFile().save_cfg("nodecolor", colorline)
            Restart().run()
        else:
            pass

    @staticmethod
    def choose_map():
        mapname = tkFileDialog.askopenfilename(initialdir="maps")
        if not mapname or not mapname.lower().endswith(('.png', '.jpg', '.jpeg')):
            tkMessageBox.showinfo("", message="Error, select png/jpg/jpeg files only.\n Loading default map now.")
            mapname = "maps/directKiwi_map_grayscale_with_sea.jpg"
        ReadConfigFile().read_cfg()
        SaveConfigFile().save_cfg("mapc", "maps/" + os.path.split(mapname)[1])
        Restart().run()

    def runupdate(self):  # if UPDATE button is pushed
        self.Button3.configure(state="disabled")
        CheckUpdate(self).start()  # start the update thread

    # ---------------------------------------------------MAIN-----------------------------------------------------------

    def feedsmeter(self, rssi):  # as mentionned, feed the s-meter progress bar with RSSI values from socket
        self.TProgressbar1["value"] = rssi

    @staticmethod
    def checkversion():
        try:
            checkver = requests.get('https://raw.githubusercontent.com/llinkz/directKiwi/master/README.md', timeout=2)
            gitsrctext = checkver.text.split("\n")
            if float(gitsrctext[0][2:].split("v", 1)[1]) > float(VERSION.split("v", 1)[1][:4]):
                tkMessageBox.showinfo(title="UPDATE INFORMATION", message=str(gitsrctext[0][
                                                                              2:]) + " has been released !\n\nCheck https://github.com/llinkz/directKiwi for change log & update.\n\nI hope you enjoy this software\n\n73 from linkz")
            else:
                pass
        except:
            print "Unable to verify version information. Sorry."
            pass

    # def checksnr(self):  # work in progress
    #     global snrcheck, snrfreq
    #     snrcheck = True
    #     snrfreq = float(self.Entry1.get())
    #     snrfreq = snrfreq + 202.94
    #     snrfreq = str(snrfreq)


class MainW(Tk, object):

    def __init__(self):
        Tk.__init__(self)
        Tk.option_add(self, '*Dialog.msg.font', 'TkFixedFont 7')
        self.window = ZoomAdvanced(self)
        self.window2 = MainWindow(self)


def on_closing():
    global proc_pid
    if tkMessageBox.askokcancel("Quit", "Do you want to quit?"):
        try:  # to kill kiwirecorder.py
            os.kill(proc_pid, signal.SIGTERM)
        except:
            pass
        os.kill(os.getpid(), signal.SIGTERM)
        app.destroy()


if __name__ == '__main__':
    app = MainW()
    app.title(VERSION)
    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()
