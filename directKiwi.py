#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" DirectKiwi python code. """

# python 2/3 compatibility
from __future__ import print_function
from __future__ import division
# from __future__ import absolute_import

import codecs
import json
import os
import re
import signal
import subprocess
from subprocess import PIPE
import sys
import platform
import threading
import time
import webbrowser
from shutil import copyfile
from collections import OrderedDict
import requests
from PIL import Image, ImageTk

# python 2/3 compatibility
if sys.version_info[0] == 2:
    import tkFileDialog
    import tkMessageBox
    import ttk
    from Tkinter import Checkbutton, END, CURRENT, NORMAL, Message, Scale
    from Tkinter import Entry, Text, Menu, Label, Button, Frame, Tk, Canvas, PhotoImage
    from tkColorChooser import askcolor
else:
    import tkinter.filedialog as tkFileDialog
    import tkinter.messagebox as tkMessageBox
    from tkinter import Checkbutton, END, CURRENT, NORMAL, Message, Scale
    from tkinter import Entry, Text, Menu, Label, Button, Frame, Tk, Canvas, PhotoImage, ttk
    from tkinter.colorchooser import askcolor


VERSION = "directKiwi v7.21"


class Restart(object):
    """ GUI Restart routine. """

    def __init__(self):
        pass

    @staticmethod
    def run():
        if platform.system() == "Windows":
            os.execlp("pythonw.exe", "pythonw.exe", "directKiwi.py")
        else:
            os.execv(sys.executable, [sys.executable] + sys.argv)


class ReadCfg(object):
    """ DirectKiwi configuration file read process. """

    def __init__(self):
        pass

    @staticmethod
    def read_cfg():
        global LP_CUT, HP_CUT, AGC, HANG, MGAIN, THRESHOLD, SLOPE, DECAY
        global CFG, DX0, DY0, DX1, DY1, DMAP, MAPFL, WHITELIST, BLACKLIST
        global STDCOLOR, FAVCOLOR, BLKCOLOR, ICONSIZE, ICONTYPE, HIGHLIGHT
        global BGC, FGC, GRAD, THRES, CONS_B, CONS_F, STAT_B, STAT_F
        # Read the config file format and declare variables
        with open('directKiwi.cfg', 'r') as config_file:
            CFG = json.load(config_file, object_pairs_hook=OrderedDict)
        # demod block
        LP_CUT, HP_CUT, AGC = CFG["demod"]["lp_cut"], CFG["demod"]["hp_cut"], CFG["demod"]["agc"]
        HANG, MGAIN = CFG["demod"]["hang"], CFG["demod"]["mgain"]
        THRESHOLD, SLOPE, DECAY = CFG["demod"]["thres"], CFG["demod"]["slope"], CFG["demod"]["decay"]
        # map block
        DX0, DX1 = CFG["map"]["x0"], CFG["map"]["x1"]
        DY0, DY1 = CFG["map"]["y0"], CFG["map"]["y1"]
        DMAP, MAPFL, ICONSIZE = CFG["map"]["file"], CFG["map"]["mapfl"], CFG["map"]["iconsize"]
        STDCOLOR, FAVCOLOR, BLKCOLOR = CFG["map"]["std"], CFG["map"]["fav"], CFG["map"]["blk"]
        HIGHLIGHT, ICONTYPE = CFG["map"]["hlt"], CFG["map"]["icontype"]
        # guicolors block
        BGC, FGC = CFG["guicolors"]["main_b"], CFG["guicolors"]["main_f"]
        CONS_B, CONS_F = CFG["guicolors"]["cons_b"], CFG["guicolors"]["cons_f"]
        STAT_B, STAT_F = CFG["guicolors"]["stat_b"], CFG["guicolors"]["stat_f"]
        THRES, GRAD = CFG["guicolors"]["thres"], CFG["guicolors"]["grad"]
        # nodes block
        WHITELIST, BLACKLIST = CFG["nodes"]["whitelist"], CFG["nodes"]["blacklist"]


class SaveCfg(object):
    """ DirectTDoA configuration file save process. """

    def __init__(self):
        pass

    @staticmethod
    def save_cfg(cat, field, field_value):
        # Sets the new parameter value to the right category
        CFG[cat][field] = field_value
        # Now save the config file
        with open('directKiwi.cfg', 'w') as config_file:
            json.dump(CFG, config_file, indent=2)


class CheckUpdate(threading.Thread):
    """ Check if the sources are up before running the RunUpdate process. """

    def __init__(self):
        super(CheckUpdate, self).__init__()

    def run(self):
        chk_linkf = 0
        APP.gui.writelog("Checking if rx.linkfanel.net is up ...")
        try:
            requests.get("http://rx.linkfanel.net/kiwisdr_com.js", timeout=2)
            requests.get("http://rx.linkfanel.net/snr.js", timeout=2)
            chk_linkf = 1
        except requests.ConnectionError:
            APP.gui.writelog("Sorry Pierre's website is not reachable. try again later.")
            APP.gui.update_button.configure(state="normal")
        if chk_linkf == 1:
            APP.gui.writelog("Ok looks good, KiwiSDR node listing update started ...")
            RunUpdate().run()


class RunUpdate(threading.Thread):
    """ Update map process """

    def __init__(self, parent=None):
        super(RunUpdate, self).__init__()
        self.parent = parent

    def run(self):
        try:
            # Get the node list from linkfanel website
            nodelist = requests.get("http://rx.linkfanel.net/kiwisdr_com.js")
            # Convert that listing to fit a JSON format (also removing bad/incomplete node entries)
            kiwilist = re.sub(r"{\n(.*?),\n(.*?),\n\t\},", "",
                              re.sub(r"},\n]\n;", "\t}\n]", re.sub(r"(//.+\n)+\n.+", "", nodelist.text, 0), 0), 0)
            json_data = json.loads(kiwilist)
            # Get the SNR list from linkfanel website
            snrlist = requests.get("http://rx.linkfanel.net/snr.js")
            # Convert that listing to fit a JSON format
            snrlist = re.sub(r"(//.+\n){2}\n.+", "", re.sub(r",\n}\n;", "\t}\n", snrlist.text, 0), 0)  # from fev 2020
            json_data2 = json.loads(snrlist)
            # Remove the existing node database
            if os.path.isfile('directKiwi_server_list.db'):
                os.remove('directKiwi_server_list.db')
            # Open a new database
            with codecs.open('directKiwi_server_list.db', 'wb', encoding='utf8') as db_file:
                db_file.write("[\n")
                # Parse linkfanel listing, line per line
                for i in range(len(json_data)):
                    # Adding display in the console window (* char for each node)
                    APP.gui.console_window.insert('end -1 lines', "*")
                    APP.gui.console_window.see('end')
                    time.sleep(0.005)
                    try:
                        # Parse the geographical coordinates
                        gpsfield = re.search(r'([-+]?[0-9]{1,2}(\.[0-9]*)?)(,| ) '
                                             r'?([-+]?[0-9]{1,3}(\.[0-9]*))?', json_data[i]['gps'][1:-1])
                        nodelat = gpsfield.group(1)
                        nodelon = gpsfield.group(4)
                    except:
                        # For admins not respecting GPS field format (nn.nnnnnn, nn.nnnnnn)
                        # => nodes will be shown at 0°LAT 0°LON
                        print("*** Error reading <gps> field")
                        nodelat = nodelon = "0"
                    # Now create a json-type line for the kiwiSDR node listing
                    try:
                        # Check if node has been measured by linkfanel's SNR script
                        try:
                            snr_search = str(int(round(float(json_data2[json_data[i]['id']]))))
                        except KeyError:
                            snr_search = "15"
                        nodeinfo = dict(
                            mac=json_data[i]['id'],
                            url=json_data[i]['url'].split('//', 1)[1],
                            lat=nodelat,
                            lon=nodelon,
                            snr=snr_search
                        )
                        ordered_dict = ['mac', 'url', 'snr', 'lat', 'lon']
                        nodelist = [(key, nodeinfo[key]) for key in ordered_dict]
                        nodeinfo = OrderedDict(nodelist)
                        json1 = json.dumps(nodeinfo, ensure_ascii=False)
                        db_file.write(json1 + ",\n")
                    except Exception as node_error:
                        print(str(node_error))
                        pass
                db_file.seek(-2, os.SEEK_END)
                db_file.truncate()
                db_file.write("\n]")
                db_file.close()
                # If update process finish normally, we can make a backup copy of the server listing
                copyfile("directKiwi_server_list.db", "directKiwi_server_list.db.bak")
                # Then we restart the GUI
                APP.gui.console_window.delete('end -1c linestart', END)
                APP.gui.console_window.insert('end', '\n')
                APP.gui.writelog("The KiwiSDR listing update has been successfully completed.")
        except ValueError as update_error:
            APP.gui.console_window.delete('end -1c linestart', END)
            APP.gui.console_window.insert('end', '\n')
            APP.gui.writelog("UPDATE FAIL - ERROR : " + str(update_error))
            copyfile("directKiwi_server_list.db.bak", "directKiwi_server_list.db")
        APP.gui.redraw()
        APP.gui.update_button.configure(state="normal")


class CheckSnr(threading.Thread):
    """ SNR check process. """

    def __init__(self, serverport):
        threading.Thread.__init__(self)
        self.s_host = serverport.rsplit(":")[0]
        self.s_port = serverport.rsplit(":")[1]

    def run(self):
        """ SNR check process. """
        try:
            socket2_connect = subprocess.Popen(
                [sys.executable, 'kiwiclient' + os.sep + 'microkiwi_waterfall.py', '-s', self.s_host, '-p',
                 self.s_port], stdout=PIPE, shell=False)
            APP.gui.writelog("Retrieving " + self.s_host + " waterfall, please wait")
            while True:
                snr_output = socket2_connect.stdout.readline()
                if b"received sample" in snr_output:
                    APP.gui.console_window.insert('end -1c', '.')
                if b"SNR" in snr_output:
                    APP.gui.console_window.delete('end -1c linestart', END)
                    APP.gui.console_window.insert('end', '\n')
                    APP.gui.writelog(snr_output.decode().replace("\n", ""))
                    break
        except ValueError:
            print("Error: unable to retrieve datas from this node")


class StartKiwiSDRclient(threading.Thread):
    """ DirectKiwi Main audio socket process. """

    def __init__(self):
        super(StartKiwiSDRclient, self).__init__()

    def run(self):
        """ DirectKiwi Main audio socket process. """
        global LISTENMODE, CLIENT_PID, LP_CUT, HP_CUT, FREQUENCY
        try:
            if AGC == 1:
                agc_array = False
            else:
                # default MGC =>  gain = 50  hang = 1  thresh = -100  slope = 6  decay = 1000
                agc_array = ['-g ' + str(MGAIN), HANG, THRESHOLD, SLOPE, DECAY]
            if platform.system() == "Windows":
                client_type = VERSION + ' [win]'
            elif platform.system() == "Darwin":
                client_type = VERSION + ' [macOS]'
            else:
                client_type = VERSION + ' [linux]'
            if MODE == 'AM':  # 9800Hz BW
                LP_CUT = -5900
                HP_CUT = 5900
            elif MODE == 'AMn':
                LP_CUT = -2500
                HP_CUT = 2500
            elif MODE == 'USB':
                LP_CUT = APP.gui.lowpass_scale.get()
                HP_CUT = APP.gui.highpass_scale.get()
            elif MODE == 'LSB':
                LP_CUT = 0 - APP.gui.highpass_scale.get()
                HP_CUT = 0 - APP.gui.lowpass_scale.get()
            elif MODE == 'CW':  # 500Hz BW , centered at 500Hz AF
                FREQUENCY = float(FREQUENCY) - 0.5  # https://github.com/jks-prv/kiwiclient/pull/54
                LP_CUT = 250
                HP_CUT = 750
            elif MODE == 'CWn':  # 60Hz BW , centered at 500Hz AF
                FREQUENCY = float(FREQUENCY) - 0.5  # https://github.com/jks-prv/kiwiclient/pull/54
                LP_CUT = 470
                HP_CUT = 530
            socket_connect = subprocess.Popen([sys.executable, 'kiwiclient' + os.sep + 'kiwirecorder.py', '-s',
                                               HOST.rsplit("$", 4)[1].rsplit(":", 2)[0], '-p',
                                               HOST.rsplit("$", 4)[1].rsplit(":", 2)[1], '-f', str(FREQUENCY), '-m',
                                               MODE, '-L', str(LP_CUT), '-H', str(HP_CUT), '-u',
                                               client_type.replace(' ', '_'), '-q', '-a',
                                               (" ,".join(map(str, agc_array)) if agc_array else ''), '--log=debug'],
                                              stdout=PIPE, shell=False)
            CLIENT_PID = socket_connect.pid
            APP.gui.stop_button.configure(state="normal")
            LISTENMODE = True
        except ValueError:
            print("error: unable to demodulate this node")
            LISTENMODE = False


class StopListen(object):
    """ Process that kills the web socket to stop listening mode. """

    def __init__(self):
        pass

    @staticmethod
    def run():
        """ Process that kills the web socket to stop listening mode. """
        global LISTENMODE
        LISTENMODE = False
        APP.gui.writelog("Stopping Listen mode")
        APP.title(VERSION)
        APP.gui.stop_button.configure(state="disabled")
        try:
            os.kill(CLIENT_PID, signal.SIGTERM)
        except ImportError:
            pass


class FillMapWithNodes(object):
    """ process to display the nodes on the World Map. """

    def __init__(self, parent):
        self.parent = parent

    def run(self):
        """ DirectTDoA process to display the nodes on the World Map. """
        global NODE_COUNT, NODE_COUNT_FILTER, tag_list
        tag_list = []
        NODE_COUNT = 0
        NODE_COUNT_FILTER = 0
        server_lists = ["directKiwi_server_list.db", "directKiwi_static_server_list.db"]
        for server_list in server_lists:
            with open(server_list) as node_db:
                db_data = json.load(node_db)
                for node_index in range(len(db_data)):
                    NODE_COUNT += 1
                    # Change icon color of fav, black and standards nodes and apply a gradiant // SNR
                    perc = (int(db_data[node_index]["snr"]) - 30) * GRAD
                    if db_data[node_index]["mac"] in WHITELIST:
                        node_color = (self.color_variant(FAVCOLOR, perc))
                    elif db_data[node_index]["mac"] in BLACKLIST:
                        node_color = (self.color_variant(BLKCOLOR, perc))
                    else:
                        node_color = (self.color_variant(STDCOLOR, perc))
                    # Apply the map filtering
                    if MAPFL == 1 and db_data[node_index]["mac"] not in BLACKLIST:
                        NODE_COUNT_FILTER += 1
                        self.add_point(node_index, node_color, db_data)
                    elif MAPFL == 2 and db_data[node_index]["mac"] in WHITELIST:
                        NODE_COUNT_FILTER += 1
                        self.add_point(node_index, node_color, db_data)
                    elif MAPFL == 3 and db_data[node_index]["mac"] in BLACKLIST:
                        NODE_COUNT_FILTER += 1
                        self.add_point(node_index, node_color, db_data)
                    elif MAPFL == 0:
                        NODE_COUNT_FILTER += 1
                        self.add_point(node_index, node_color, db_data)
        if 'APP' in globals():
            APP.gui.label04.configure(text="█ Visible: " + str(NODE_COUNT_FILTER) + "/" + str(NODE_COUNT))
        self.parent.show_image()

    @staticmethod
    def convert_lat(lat):
        """ Convert the real node latitude coordinates to adapt to GUI window map geometry. """
        # nodes are between LATITUDE 0 and 90N
        if float(lat) > 0:
            return 990 - (float(lat) * 11)
        # nodes are between LATITUDE 0 and 60S
        return 990 + (float(0 - float(lat)) * 11)

    @staticmethod
    def convert_lon(lon):
        """ Convert the real node longitude coordinates to adapt to GUI window map geometry. """
        return 1910 + ((float(lon) * 1910) / 180)

    @staticmethod
    def color_variant(hex_color, brightness_offset=1):
        """ Process that changes the brightness (only) of a specific RGB color.
        chase-seibert.github.io/blog/2011/07/29/python-calculate-lighterdarker-rgb-colors.html """
        rgb_hex = [hex_color[x:x + 2] for x in [1, 3, 5]]
        new_rgb_int = [int(hex_value, 16) + brightness_offset for hex_value in rgb_hex]
        new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int]
        return "#" + "".join(["0" + hex(i)[2:] if len(hex(i)[2:]) < 2 else hex(i)[2:] for i in new_rgb_int])

    def add_point(self, node_index_data, node_color, node_db_data):
        """ Process that add node icons over the World map. """
        global tag_list
        mykeys = ['mac', 'url', 'snr', 'lat', 'lon']
        node_lat = self.convert_lat(node_db_data[node_index_data]["lat"])
        node_lon = self.convert_lon(node_db_data[node_index_data]["lon"])
        node_tag = str('$'.join([node_db_data[node_index_data][x] for x in mykeys]))
        ic_size = int(ICONSIZE)
        try:
            if ICONTYPE == 0:
                self.parent.canvas.create_oval(node_lon - ic_size, node_lat - ic_size, node_lon + ic_size,
                                               node_lat + ic_size, fill=node_color, tag=node_tag)
            else:

                self.parent.canvas.create_rectangle(node_lon - ic_size, node_lat - ic_size, node_lon + ic_size,
                                                    node_lat + ic_size, fill=node_color, tag=node_tag)
            self.parent.canvas.tag_bind(node_tag, "<Button-1>", self.parent.onclickleft)
            self.parent.canvas.tag_bind(node_tag, "<Button-3>", self.parent.onclickright)
            tag_list.append(node_tag)
        except NameError:
            print("OOPS - Error in adding the point to the map")

    def delete_point(self, map_definition):
        """ Map presets deletion process. """
        self.parent.canvas.delete(map_definition)

    def redraw_map(self):
        """ Redraw all icons on the World Map. """
        for node_tag_item in tag_list:
            self.parent.canvas.delete(node_tag_item)
        ReadCfg().read_cfg()
        FillMapWithNodes.run(self)

    def node_sel_active(self, node_mac):
        """ Adding additionnal highlight on node icon. """
        for node_tag_item in tag_list:
            if node_mac in node_tag_item:
                tmp_latlon = node_tag_item.rsplit("$", 4)
                tmp_lat = self.convert_lat(tmp_latlon[3])
                tmp_lon = self.convert_lon(tmp_latlon[4])
                is_delta = int(ICONSIZE) + 1
                if ICONTYPE == 0:
                    self.parent.canvas.create_oval(tmp_lon - is_delta, tmp_lat - is_delta, tmp_lon + is_delta,
                                                   tmp_lat + is_delta, fill='', outline=HIGHLIGHT,
                                                   tag=node_tag_item + "$#")
                else:
                    self.parent.canvas.create_rectangle(tmp_lon - is_delta, tmp_lat - is_delta, tmp_lon + is_delta,
                                                        tmp_lat + is_delta, fill='', outline=HIGHLIGHT,
                                                        tag=node_tag_item + "$#")
                self.parent.canvas.tag_bind(node_tag_item + "$#", "<Button-1>", self.parent.onclickleft)

    def node_selection_inactive(self, node_mac):
        """ Removing additionnal highlight on selected node icon. """
        for node_tag_item in tag_list:
            if node_mac in node_tag_item:
                self.parent.canvas.tag_unbind(node_tag_item + "$#", "<Button-1>")
                self.parent.canvas.delete(node_tag_item + "$#")

    def node_selection_inactiveall(self):
        """ Removing ALL additionnal highlights on selected nodes icons. """
        for node_tag_item in tag_list:
            self.parent.canvas.tag_unbind(node_tag_item + "$#", "<Button-1>")
            self.parent.canvas.delete(node_tag_item + "$#")

    def after_update(self):
        ReadCfg().read_cfg()
        FillMapWithNodes.run(self)


class GuiCanvas(Frame):
    """ Process that creates the GUI map canvas, enabling move & zoom on a picture.
    source: stackoverflow.com/questions/41656176/tkinter-canvas-zoom-move-pan?noredirect=1&lq=1 """

    def __init__(self, parent):
        Frame.__init__(self, parent=None)
        # tip: GuiCanvas is member1
        parent.geometry("1050x600+200+50")  # directKiwi
        # parent.geometry("1200x700+150+10")  # directTDoA
        img = PhotoImage(file='icon.gif')
        parent.after(50, parent.call('wm', 'iconphoto', parent, img))
        global LISTENMODE
        LISTENMODE = False
        ReadCfg().read_cfg()
        self.x = self.y = 0
        # Create canvas and put image on it
        self.canvas = Canvas(self.master, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky='nswe')
        self.canvas.update()  # wait till canvas is created
        # Make the canvas expandable
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        # Bind events to the Canvas
        self.canvas.bind('<Configure>', self.show_image)  # canvas is resized
        self.canvas.bind('<ButtonPress-1>', self.move_from)  # map move
        self.canvas.bind('<B1-Motion>', self.move_to)  # map move
        # self.canvas.bind_all('<MouseWheel>', self.wheel)  # Windows Zoom
        # self.canvas.bind('<Button-5>', self.wheel)  # Linux Zoom
        # self.canvas.bind('<Button-4>', self.wheel)  # Linux Zoom
        self.image = Image.open(DMAP)
        self.width, self.height = self.image.size
        self.imscale = 1.0  # scale for the image
        self.delta = 2.0  # zoom magnitude
        # Put image into container rectangle and use it to set proper coordinates to the image
        self.container = self.canvas.create_rectangle(0, 0, self.width, self.height, width=0)
        self.canvas.config(scrollregion=(0, 0, self.width, self.height))
        self.rect = None
        self.start_x = None
        self.start_y = None
        self.canvas.scan_dragto(-int(DX0.split('.')[0]), -int(DY0.split('.')[0]), gain=1)
        self.show_image()
        # time.sleep(0.02)
        FillMapWithNodes(self).run()

    def unselect_allpoint(self):
        """ Calling process that remove additionnal highlight on all selected nodes. """
        FillMapWithNodes(self).node_selection_inactiveall()

    def redraw_map_cmd(self):
        """ Calling process that redraw all icons on the World map. """
        FillMapWithNodes(self).redraw_map()

    def delete_point(self, n):
        """ KnownPoint deletion process. """
        FillMapWithNodes(self).delete_point(n.rsplit(' (')[0])

    def onclickright(self, event=None):
        """ Right Mouse Click bind to show node general menu. """
        global HOST
        menu0 = Menu(self, tearoff=0, fg="black", bg=BGC, font='TkFixedFont 7')  # node overlap list menu
        menu1 = Menu(self, tearoff=0, fg="black", bg=BGC, font='TkFixedFont 7')  # main node menu
        # search for overlapping nodes
        overlap_range = ICONSIZE * 4
        overlap_rect = (self.canvas.canvasx(event.x) - overlap_range), (self.canvas.canvasy(event.y) - overlap_range), (
                    self.canvas.canvasx(event.x) + overlap_range), (self.canvas.canvasy(event.y) + overlap_range)
        node_overlap_match = self.canvas.find_enclosed(*overlap_rect)
        if len(node_overlap_match) > 1:  # node icon overlap found, displays menu0
            for el1, el2 in enumerate(node_overlap_match):
                if "$#" not in str(self.canvas.gettags(el2)):  # dont display node highlight tags
                    HOST = self.canvas.gettags(self.canvas.find_withtag(el2))[0]
                    # mykeys = ['mac', 'url', 'snr', 'lat', 'lon']
                    # n_field    0      1      2      3      4
                    n_field = HOST.rsplit("$", 4)
                    # Color gradiant proportionnal to SNR value
                    snr_gradiant = (int(n_field[2]) - 30) * GRAD
                    # rbg = self.color_variant("#FF0000", snr_gradiant)
                    # Dynamic foreground (adapting font to white or black depending on luminosity)
                    dfg = self.get_font_color((self.color_variant("#FFFF00", snr_gradiant)))
                    nodec = BLKCOLOR if n_field[0] in BLACKLIST else FAVCOLOR if n_field[0] in WHITELIST else STDCOLOR
                    cbg = self.color_variant(nodec, snr_gradiant)
                    menu0.add_command(label=n_field[1], background=cbg, foreground=dfg,
                                      command=lambda x=HOST: self.create_node_menu(x, event.x_root, event.y_root,
                                                                                   menu1))
                else:
                    pass
            menu0.tk_popup(event.x_root, event.y_root)
        else:
            HOST = self.canvas.gettags(self.canvas.find_withtag(CURRENT))[0]
            self.create_node_menu(HOST, event.x_root, event.y_root, menu1)

    def onclickleft(self, event):
        """ Left Mouse Click bind to start demodulation from the node. """
        global HOST
        menu0 = Menu(self, tearoff=0, fg="black", bg=BGC, font='TkFixedFont 7')  # node overlap list menu
        # search for overlapping nodes
        overlap_range = ICONSIZE * 4
        overlap_rect = (self.canvas.canvasx(event.x) - overlap_range), (self.canvas.canvasy(event.y) - overlap_range), (
                    self.canvas.canvasx(event.x) + overlap_range), (self.canvas.canvasy(event.y) + overlap_range)
        node_overlap_match = self.canvas.find_enclosed(*overlap_rect)
        if len(node_overlap_match) > 1:  # node icon overlap found, displays menu0
            for el1, el2 in enumerate(node_overlap_match):
                if "$#" not in str(self.canvas.gettags(el2)):  # dont display node highlight tags
                    HOST = self.canvas.gettags(self.canvas.find_withtag(el2))[0]
                    # mykeys = ['mac', 'url', 'snr', 'lat', 'lon']
                    # n_field    0      1      2      3      4
                    n_field = HOST.rsplit("$", 4)
                    # Color gradiant proportionnal to SNR value
                    snr_gradiant = (int(n_field[2]) - 30) * GRAD
                    # Dynamic foreground (adapting font to white or black depending on luminosity)
                    dfg = self.get_font_color((self.color_variant("#FFFF00", snr_gradiant)))
                    nodec = BLKCOLOR if n_field[0] in BLACKLIST else FAVCOLOR if n_field[0] in WHITELIST else STDCOLOR
                    cbg = self.color_variant(nodec, snr_gradiant)

                    menu0.add_command(label=n_field[1], background=cbg, foreground=dfg,
                                      command=lambda x=HOST: self.start_listen(x))
                else:
                    pass
            menu0.tk_popup(event.x_root, event.y_root)
        else:
            HOST = self.canvas.gettags(self.canvas.find_withtag(CURRENT))[0]
            self.start_listen(HOST)

    def start_listen(self, kiwinodetag):
        global HOST, FREQUENCY, LISTENMODE, CLIENT_PID
        n_field = kiwinodetag.rsplit("$", 4)
        permit_web = "no"
        FREQUENCY = APP.gui.freq_input.get()
        if FREQUENCY == "" or float(FREQUENCY) < 5 or float(FREQUENCY) > 29995:
            APP.gui.writelog("Check FREQUENCY field !")
        else:
            try:  # check if the node is answering
                chktimeout = 2  # timeout of the node check
                checkthenode = requests.get("http://" + n_field[1] + "/status", timeout=chktimeout)
                i_node = []
                try:
                    for line in checkthenode.text.splitlines():
                        i_node.append(line.rsplit("=", 1)[1])
                    # i_node = each parameter of the retrieved "address:port/status" webpage lines
                    # 0 = status (private / public)    10 = good received GPS sats
                    # 1 = offline (no / yes)           11 = total GPS fixes
                    # 2 = name                         12 = GPS fixes per minute (max = 30)
                    # 3 = sdr_hw                       13 = GPS fixes per hour
                    # 4 = op_email                     14 = TDoA id
                    # 5 = bands (KiwiSDR freq range)   15 = TDoA receiver slots
                    # 6 = users                        16 = Receiver altitude
                    # 7 = max users                    17 = Receiver location
                    # 8 = avatar ctime                 18 = Software version
                    # 9 = gps coordinates              19 = Antenna description
                    # 20 = KiwiSDR uptime (in sec)
                    if i_node[6] == i_node[7]:  # users Vs. users_max
                        APP.gui.writelog(" " + n_field[1].rsplit(":", 2)[0] + " is full.")
                    elif i_node[1] == "yes":  # offline=no/yes
                        APP.gui.writelog(" " + n_field[1].rsplit(":", 2)[0] + " is offline.")
                    else:
                        permit_web = "yes"
                except IndexError as wrong_status:
                    APP.gui.writelog("Sorry " + n_field[1].rsplit(":", 2)[0] + " is unreachable.")
            except requests.RequestException:
                APP.gui.writelog("Sorry " + n_field[1].rsplit(":", 2)[0] + " is unreachable.")
            if permit_web == "yes":
                if not LISTENMODE:
                    StartKiwiSDRclient().start()
                    self.populate("add", n_field)
                else:
                    try:
                        os.kill(CLIENT_PID, signal.SIGTERM)
                        StartKiwiSDRclient().start()
                        self.unselect_allpoint()
                        self.populate("add", n_field)
                    except NameError:
                        pass
                APP.gui.writelog(" ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ")
                APP.gui.writelog("[ " + n_field[1].rsplit(":", 2)[0] + " / " + str(FREQUENCY) + " kHz / " + str(
                    MODE).upper() + " / " + str(HP_CUT - LP_CUT) + "Hz ]")
                APP.title(
                    str(VERSION) + " - [ " + n_field[1].rsplit(":", 2)[0] + " / " + str(FREQUENCY) + " kHz / " + str(
                        MODE).upper() + " / " + str(HP_CUT - LP_CUT) + "Hz ]")

    def create_node_menu(self, kiwinodetag, popx, popy, menu):
        n_field = kiwinodetag.rsplit("$", 4)
        snr_gradiant = (int(n_field[2]) - 30) * GRAD
        nodec = BLKCOLOR if n_field[0] in BLACKLIST else FAVCOLOR if n_field[0] in WHITELIST else STDCOLOR
        # Red background
        rbg = self.color_variant("#FF0000", snr_gradiant)
        # Dynamic foreground (adapting font to white or black depending on luminosity)
        dfg = self.get_font_color((self.color_variant("#FFFF00", snr_gradiant)))
        # Colorized background (depending on Favorite node or not)
        cbg = self.color_variant(nodec, snr_gradiant)
        try:  # check if the node is answering
            chktimeout = 2  # timeout of the node check
            checkthenode = requests.get("http://" + n_field[1] + "/status", timeout=chktimeout)
            i_node = []
            try:
                for line in checkthenode.text.splitlines():
                    i_node.append(line.rsplit("=", 1)[1])
                # i_node = each parameter of the retrieved "address:port/status" webpage lines
                # 0 = status (private / public)    10 = good received GPS sats
                # 1 = offline (no / yes)           11 = total GPS fixes
                # 2 = name                         12 = GPS fixes per minute (max = 30)
                # 3 = sdr_hw                       13 = GPS fixes per hour
                # 4 = op_email                     14 = TDoA id
                # 5 = bands (KiwiSDR freq range)   15 = TDoA receiver slots
                # 6 = users                        16 = Receiver altitude
                # 7 = max users                    17 = Receiver location
                # 8 = avatar ctime                 18 = Software version
                # 9 = gps coordinates              19 = Antenna description
                # 20 = KiwiSDR uptime (in sec)
                permit_web = False
                n_stat = " [" + i_node[6] + "/" + i_node[7] + " users]"
                g_stat = " [GNSS: " + i_node[12] + " fixes/min] [GPS: " + i_node[10] + "/12]"
                s_stat = " [SNR: " + n_field[2] + " dB]"
                # If no socket slots are available on this node :
                if i_node[6] == i_node[7]:
                    menu.add_command(label=n_field[1] + " is full" + g_stat + n_stat + s_stat, background=rbg,
                                     foreground=dfg, command=None)
                # If node is offline :
                elif i_node[1] == "yes":
                    menu.add_command(label=n_field[1] + " is offline", background=rbg, foreground=dfg, command=None)
                # If node had no GPS fix in the last minute :
                else:  # All is ok for this node and then, permit extra commands
                    permit_web = True
            except IndexError as wrong_status:
                menu.add_command(label=n_field[1] + " is not available. (proxy.kiwisdr.com error)", background=rbg,
                                 foreground=dfg, command=None)
                permit_web = False
        except requests.exceptions.ConnectionError as req_conn_error:
            menu.add_command(label=n_field[1] + " node is not available. " + str(req_conn_error).split('\'')[1::2][1],
                             background=rbg, foreground=dfg, command=None)
            permit_web = False
        except requests.exceptions.RequestException as req_various_error:
            menu.add_command(label=n_field[1] + " node is not available. " + str(req_various_error), background=rbg,
                             foreground=dfg, command=None)
            permit_web = False

        # Always try to print out KiwiSDR's full name line
        try:
            menu.add_command(label=i_node[2] + g_stat + n_stat + s_stat, state=NORMAL, background=cbg, foreground=dfg,
                             command=None)
        except (UnboundLocalError, IndexError):
            pass

        # EXTRA commands and lines
        if permit_web and APP.gui.freq_input.get() != "" and 5 < float(APP.gui.freq_input.get()) < 30000:
            # Add Open in Web browser lines
            menu.add_separator()
            menu.add_command(label="Open " + n_field[1] + " in Web browser", state=NORMAL, background=cbg,
                             foreground=dfg, command=lambda: self.openinbrowser(n_field, 0, APP.gui.freq_input.get()))
            menu.add_command(label="Open " + n_field[1] + " in Web browser with pre-set TDoA extension loaded",
                             state=NORMAL, background=cbg, foreground=dfg,
                             command=lambda: self.openinbrowser(n_field, 1, APP.gui.freq_input.get()))
            menu.add_command(label="Open " + n_field[1] + "/status", background=cbg, foreground=dfg,
                             command=lambda: self.openinbrowser(n_field, 2, None))
        if permit_web:
            menu.add_command(label="Get Waterfall & SNR from " + n_field[1], background=cbg, foreground=dfg,
                             command=CheckSnr(n_field[1]).start)
        menu.add_separator()
        if n_field[0] in WHITELIST:  # if node is a favorite
            menu.add_command(label="remove from favorites", background=cbg, foreground=dfg,
                             command=lambda x=n_field[0]: self.remfavorite(x))
        elif n_field[0] not in BLACKLIST:
            menu.add_command(label="add to favorites", background=cbg, foreground=dfg,
                             command=lambda x=n_field[0]: self.addfavorite(x))
        if n_field[0] in BLACKLIST:  # if node is blacklisted
            menu.add_command(label="remove from blacklist", background=cbg, foreground=dfg,
                             command=lambda x=n_field[0]: self.remblacklist(x))
        elif n_field[0] not in WHITELIST:
            menu.add_command(label="add to blacklist", background=cbg, foreground=dfg,
                             command=lambda x=n_field[0]: self.addblacklist(x))
        menu.tk_popup(int(popx), int(popy))  # popup placement // node icon

    @staticmethod
    def get_font_color(font_color):
        """ Adapting the foreground font color regarding background luminosity.
        stackoverflow questions/946544/good-text-foreground-color-for-a-given-background-color """
        rgb_hex = [font_color[x:x + 2] for x in [1, 3, 5]]
        threshold = THRES  # default = 186
        if int(rgb_hex[0], 16) * 0.299 + int(rgb_hex[1], 16) * 0.587 + int(rgb_hex[2], 16) * 0.114 > threshold:
            return "#000000"
        # else:
        return "#ffffff"
        # if (red*0.299 + green*0.587 + blue*0.114) > 186 use #000000 else use #ffffff

    @staticmethod
    def color_variant(hex_color, brightness_offset=1):
        """ Routine used to change color brightness according to SNR scaled value.
        chase-seibert.github.io/blog/2011/07/29/python-calculate-lighterdarker-rgb-colors.html """
        rgb_hex = [hex_color[x:x + 2] for x in [1, 3, 5]]
        new_rgb_int = [int(hex_value, 16) + brightness_offset for hex_value in rgb_hex]
        new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int]
        return "#" + "".join(["0" + hex(i)[2:] if len(hex(i)[2:]) < 2 else hex(i)[2:] for i in new_rgb_int])

    @staticmethod
    def addfavorite(node):
        """ Add Favorite node submenu entry. """
        WHITELIST.append(node)
        SaveCfg().save_cfg("nodes", "whitelist", WHITELIST)
        APP.gui.redraw()

    @staticmethod
    def remfavorite(node):
        """ Remove Favorite node submenu entry. """
        WHITELIST.remove(node)
        SaveCfg().save_cfg("nodes", "whitelist", WHITELIST)
        APP.gui.redraw()

    @staticmethod
    def addblacklist(node):
        """ Add Blacklist node submenu entry. """
        BLACKLIST.append(node)
        SaveCfg().save_cfg("nodes", "blacklist", BLACKLIST)
        APP.gui.redraw()

    @staticmethod
    def remblacklist(node):
        """ Remove Blacklist node submenu entry. """
        BLACKLIST.remove(node)
        SaveCfg().save_cfg("nodes", "blacklist", BLACKLIST)
        APP.gui.redraw()

    @staticmethod
    def openinbrowser(node_id, extension, freq):
        """ Web browser call to connect on the node (default = IQ mode & fixed zoom level at 8). """
        if extension == 0:
            url = "http://" + node_id[1] + "/?f=" + freq + MODE.lower() + "z8"
        elif extension == 2:
            url = "http://" + node_id[1] + "/status"
        else:
            url = "http://" + node_id[1] + "/?f=" + freq + "iqz8&ext=tdoa,lat:" + node_id[3] + ",lon:" + node_id[
                4] + ",z:5"
        webbrowser.open_new(url)

    def populate(self, action, sel_node_tag):
        """ highlight node process. """
        if action == "add":
            FillMapWithNodes(self).node_sel_active(sel_node_tag[0])
        else:
            FillMapWithNodes(self).node_selection_inactive(sel_node_tag[0])

    def move_from(self, event):
        """ Move from. """
        self.canvas.scan_mark(event.x, event.y)

    def move_to(self, event):
        """ Move to. """
        if 'HOST' in globals() and "current" not in self.canvas.gettags(self.canvas.find_withtag(CURRENT))[0]:
            pass
        elif "current" in self.canvas.gettags(self.canvas.find_withtag(CURRENT))[0]:
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            self.show_image()  # redraw the image

    def wheel(self, event):
        """ Routine for mouse wheel actions. """
        x_eve = self.canvas.canvasx(event.x)
        y_eve = self.canvas.canvasy(event.y)
        bbox = self.canvas.bbox(self.container)  # get image area
        if bbox[0] < x_eve < bbox[2] and bbox[1] < y_eve < bbox[3]:
            pass  # Ok! Inside the image
        else:
            return  # zoom only inside image area
        scale = 1.0
        # Respond to Linux (event.num) or Windows (event.delta) wheel event
        if event.num == 5 or event.delta == -120:  # scroll down
            i = min(self.width, self.height)
            if int(i * self.imscale) < 2000:
                return  # block zoom if image is less than 2000 pixels
            self.imscale /= self.delta
            scale /= self.delta
        if event.num == 4 or event.delta == 120:  # scroll up
            i = min(self.canvas.winfo_width(), self.canvas.winfo_height())
            if i < self.imscale:
                return  # 1 pixel is bigger than the visible area
            self.imscale *= self.delta
            scale *= self.delta
        # rescale all canvas objects
        # scale = 2.0 or 0.5
        self.canvas.scale('all', x_eve, y_eve, scale, scale)
        # self.canvas.scale('')
        self.show_image()

    def show_image(self, event=None):
        """ Creating the canvas with the picture. """
        global b_box2
        b_box1 = self.canvas.bbox(self.container)  # get image area
        # Remove 1 pixel shift at the sides of the bbox1
        b_box1 = (b_box1[0] + 1, b_box1[1] + 1, b_box1[2] - 1, b_box1[3] - 1)
        b_box2 = (self.canvas.canvasx(0),  # get visible area of the canvas
                  self.canvas.canvasy(0),
                  self.canvas.canvasx(self.canvas.winfo_width()),
                  self.canvas.canvasy(self.canvas.winfo_height()))
        bbox = [min(b_box1[0], b_box2[0]), min(b_box1[1], b_box2[1]),  # get scroll region box
                max(b_box1[2], b_box2[2]), max(b_box1[3], b_box2[3])]
        if bbox[0] == b_box2[0] and bbox[2] == b_box2[2]:  # whole image in the visible area
            bbox[0] = b_box1[0]
            bbox[2] = b_box1[2]
        if bbox[1] == b_box2[1] and bbox[3] == b_box2[3]:  # whole image in the visible area
            bbox[1] = b_box1[1]
            bbox[3] = b_box1[3]
        self.canvas.configure(scrollregion=bbox)  # set scroll region
        x_1 = max(b_box2[0] - b_box1[0], 0)  # get coordinates (x1,y1,x2,y2) of the image tile
        y_1 = max(b_box2[1] - b_box1[1], 0)
        x_2 = min(b_box2[2], b_box1[2]) - b_box1[0]
        y_2 = min(b_box2[3], b_box1[3]) - b_box1[1]
        if int(x_2 - x_1) > 0 and int(y_2 - y_1) > 0:  # show image if it in the visible area
            x = min(int(x_2 / self.imscale), self.width)  # sometimes it is larger on 1 pixel...
            y = min(int(y_2 / self.imscale), self.height)  # ...and sometimes not
            image = self.image.crop((int(x_1 / self.imscale), int(y_1 / self.imscale), x, y))
            imagetk = ImageTk.PhotoImage(image.resize((int(x_2 - x_1), int(y_2 - y_1))))
            imageid = self.canvas.create_image(max(b_box2[0], b_box1[0]), max(b_box2[1], b_box1[1]),
                                               anchor='nw', image=imagetk)
            self.canvas.lower(imageid)  # set image into background
            self.canvas.imagetk = imagetk  # keep an extra reference to prevent garbage-collection


class MainWindow(Frame):
    """ GUI design definitions. """

    def __init__(self, parent):
        Frame.__init__(self, parent)
        self.member1 = GuiCanvas(parent)
        global MODE
        dfgc = '#a3a3a3'  # GUI (disabled) foreground color
        la_f = "TkFixedFont 7 bold"
        # Control panel background
        self.ctrl_backgd = Label(parent)
        self.ctrl_backgd.place(relx=0, rely=0.8, relheight=0.3, relwidth=1)
        self.ctrl_backgd.configure(bg=BGC, fg=FGC, width=214)

        # Map Legend
        self.label01 = Label(parent)
        self.label01.place(x=0, y=0, height=14, width=100)
        self.label01.configure(bg="black", font=la_f, anchor="w", fg=STDCOLOR, text="█ Standard")
        self.label02 = Label(parent)
        self.label02.place(x=0, y=14, height=14, width=100)
        self.label02.configure(bg="black", font=la_f, anchor="w", fg=FAVCOLOR, text="█ Favorite")
        self.label03 = Label(parent)
        self.label03.place(x=0, y=28, height=14, width=100)
        self.label03.configure(bg="black", font=la_f, anchor="w", fg=BLKCOLOR, text="█ Blacklisted")
        self.label04 = Label(parent)
        self.label04.place(x=0, y=42, height=14, width=100)
        self.label04.configure(bg="black", font=la_f, anchor="w", fg="white",
                               text="█ Visible: " + str(NODE_COUNT_FILTER) + "/" + str(NODE_COUNT))

        # Control Legend
        self.label1 = Label(parent)
        self.label1.place(relx=0.605, rely=0.95)
        self.label1.configure(bg=BGC, font="TkFixedFont", fg=FGC, text="Freq:")
        self.label2 = Label(parent)
        self.label2.place(relx=0.72, rely=0.95)
        self.label2.configure(bg=BGC, font="TkFixedFont", fg=FGC, text="kHz")

        # Frequency entry field
        self.freq_input = Entry(parent)
        self.freq_input.place(relx=0.65, rely=0.948, height=23, width=80)
        self.freq_input.configure(bg=BGC, fg=FGC, font="TkFixedFont", insertbackground=FGC, width=218)
        self.freq_input.bind('<Control-a>', self.ctrla)
        self.freq_input.focus_set()

        # Stop Listen button
        self.stop_button = Button(parent)
        self.stop_button.place(relx=0.828, rely=0.95, height=24, width=80)
        self.stop_button.configure(activebackground=BGC, activeforeground=FGC, bg="red", disabledforeground=dfgc,
                                   fg="black", highlightbackground=BGC, highlightcolor=FGC, pady="0",
                                   text="Stop", command=lambda *args: [StopListen().run(), FillMapWithNodes(
                                    self.member1).node_selection_inactiveall()], state="disabled")
        # Update button
        self.update_button = Button(parent)
        self.update_button.place(relx=0.915, rely=0.95, height=24, width=80)
        self.update_button.configure(activebackground=BGC, activeforeground=FGC, bg="orange", disabledforeground=dfgc,
                                     fg="black", highlightbackground=BGC, highlightcolor=FGC, pady="0",
                                     text="Update", command=self.runupdate, state="normal")
        # Console window
        self.console_window = Text(parent)
        self.console_window.place(relx=0.000, rely=0.8, relheight=0.2, relwidth=0.590)
        self.console_window.configure(bg=CONS_B, font="TkTextFont", fg=CONS_F, highlightbackground=BGC,
                                      highlightcolor=FGC, insertbackground=FGC, selectbackground="#c4c4c4",
                                      selectforeground=FGC, undo="1", width=970, wrap="word")
        # Low pass filter scale
        self.lowpass_scale = Scale(parent, from_=0, to=6000)
        self.lowpass_scale.place(relx=0.6, rely=0.8, relwidth=0.39, height=40)
        self.lowpass_scale.set(LP_CUT)
        self.lowpass_scale.configure(activebackground=BGC, background=BGC, foreground=FGC, highlightbackground=BGC,
                                     highlightcolor=BGC, orient="horizontal", showvalue="0", troughcolor=dfgc,
                                     resolution=10, label="Low Pass Filter (" + str(LP_CUT) + "Hz)", highlightthickness=0, command=self.changelpvalue)
        # High pass filter scale
        self.highpass_scale = Scale(parent, from_=0, to=6000)
        self.highpass_scale.place(relx=0.6, rely=0.87, relwidth=0.39, height=40)
        self.highpass_scale.set(HP_CUT)
        self.highpass_scale.configure(activebackground=BGC, background=BGC, foreground=FGC, highlightbackground=BGC,
                                      highlightcolor=BGC, orient="horizontal", showvalue="0", troughcolor=dfgc,
                                      resolution=10, label="High Pass Filter (" + str(HP_CUT) + "Hz)", highlightthickness=0, command=self.changehpvalue)
        # Modulation Combobox
        self.modulation_box = ttk.Combobox(parent, state="readonly")
        self.modulation_box.place(relx=0.755, rely=0.948, height=24, relwidth=0.06)
        self.modulation_box.configure(font="TkTextFont", values=["USB", "LSB", "AM", "AMn", "CW", "CWn"])
        self.modulation_box.current(0)
        self.modulation_box.bind("<<ComboboxSelected>>", self.modechoice)
        MODE = 'USB'
        # Adding some texts to console window at program start
        self.writelog("DirectKiwi " + VERSION)
        self.writelog("Low Pass Cut Filter [" + str(LP_CUT) + "Hz] - High Pass Cut Filter [" + str(HP_CUT) + "Hz]")
        if AGC == 1:
            self.writelog("AGC is [ON]")
        elif AGC == 0 and HANG == 0:
            self.writelog("MGC is [ON] - [Gain " + str(MGAIN) + "dB] - Hang [OFF] - Threshold [" + str(
                THRESHOLD) + "dB] - Slope [" + str(SLOPE) + "dB] - Decay [" + str(DECAY).replace("\n", "") + "ms]")
        else:
            self.writelog("MGC is [ON] - Gain [" + str(MGAIN) + "dB] - Hang [ON] - Threshold [" + str(
                THRESHOLD) + "dB] - Slope [" + str(SLOPE) + "dB] - Decay [" + str(DECAY).replace("\n", "") + "ms]")
        self.writelog(str(NODE_COUNT) + " KiwiSDRs listed.")
        self.writelog("LEFT click to start listening; RIGHT click for information.")

        # GUI topbar menus
        menubar = Menu(self)
        parent.config(menu=menubar)

        # Audio Settings Menu
        menubar.add_command(label="Audio Settings", command=self.show_demod_config)

        # Map Settings menu
        menu_1 = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Map Settings", menu=menu_1)
        sm1 = Menu(menu_1, tearoff=0)
        sm2 = Menu(menu_1, tearoff=0)
        sm3 = Menu(menu_1, tearoff=0)
        sm4 = Menu(menu_1, tearoff=0)
        menu_1.add_cascade(label='Default map', menu=sm1, underline=0)
        menu_1.add_command(label="Save map position", command=self.set_map_position)
        menu_1.add_cascade(label='Map Filters', menu=sm2, underline=0)
        menu_1.add_cascade(label='Set Colors', menu=sm3, underline=0)
        menu_1.add_cascade(label='Set Icon type', menu=sm4, underline=0)
        menu_1.add_command(label='Set Icon size', command=lambda *args: self.default_icon_size())
        sm1.add_command(label="Browse maps folder", command=self.choose_map)
        sm2.add_command(label="All", command=lambda *args: [SaveCfg().save_cfg("map", "mapfl", 0), self.redraw()])
        sm2.add_command(label="Std+Fav", command=lambda *args: [SaveCfg().save_cfg("map", "mapfl", 1), self.redraw()])
        sm2.add_command(label="Fav", command=lambda *args: [SaveCfg().save_cfg("map", "mapfl", 2), self.redraw()])
        sm2.add_command(label="Black", command=lambda *args: [SaveCfg().save_cfg("map", "mapfl", 3), self.redraw()])
        sm3.add_command(label="Standard node color", command=lambda *args: self.color_change(0))
        sm3.add_command(label="Favorite node color", command=lambda *args: self.color_change(1))
        sm3.add_command(label="Blacklisted node color", command=lambda *args: self.color_change(2))
        sm3.add_command(label="Icon highlight color", command=lambda *args: self.color_change(4))
        sm4.add_command(label="⚫", command=lambda *args: [SaveCfg().save_cfg("map", "icontype", 0), self.redraw()])
        sm4.add_command(label="■", command=lambda *args: [SaveCfg().save_cfg("map", "icontype", 1), self.redraw()])

        # GUI design
        menu_4 = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="GUI design", menu=menu_4)
        sm5 = Menu(menu_4, tearoff=0)
        menu_4.add_command(label="GUI background color", command=lambda *args: self.color_change(5))
        menu_4.add_cascade(label='Console', menu=sm5, underline=0)
        sm5.add_command(label="background color", command=lambda *args: self.color_change(6))
        sm5.add_command(label="foreground color", command=lambda *args: self.color_change(7))
        menu_4.add_command(label="SNR gradiant ratio", command=lambda *args: self.gradiant_change())
        menu_4.add_command(label="White/Black font color threshold", command=lambda *args: self.threshold_change())

        # About menu
        menu_6 = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="?", menu=menu_6)
        menu_6.add_command(label="Help", command=self.help)
        menu_6.add_command(label="About", command=self.about)
        menu_6.add_command(label="Update check", command=lambda *args: self.checkversion(source="from_menu"))

        # Check if new version is available at program start
        self.checkversion(source="at_start")

    def redraw(self):
        self.member1.redraw_map_cmd()

    def modechoice(self, event=None):
        """ Reading the typed FREQUENCY in the FREQUENCY entry box. """
        global MODE
        MODE = self.modulation_box.get()
        if MODE == 'LSB':
            self.lowpass_scale.configure(label="High Pass Filter (" + str(APP.gui.lowpass_scale.get()) + "Hz)")
            self.highpass_scale.configure(label="Low Pass Filter (" + str(APP.gui.highpass_scale.get()) + "Hz)")
        else:
            self.lowpass_scale.configure(label="Low Pass Filter (" + str(APP.gui.lowpass_scale.get()) + "Hz)")
            self.highpass_scale.configure(label="High Pass Filter (" + str(APP.gui.highpass_scale.get()) + "Hz)")

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
            APP.gui.save_demod_cfg(None, agc=0)
        else:
            tk_demod_cfg.geometry("330x128+200+200")
            ctrlb.configure(text="Automatic Gain Control Active")
            APP.gui.save_demod_cfg(None, agc=1)
        ReadCfg().read_cfg()

    @staticmethod
    def hang_button(hangb, **kwargs):
        """ DirectKiwi demodulation config window HANG button actions. """
        if kwargs.get('hang') == 1:
            hangb.configure(relief="raised")
            APP.gui.save_demod_cfg(None, hang=0)
        else:
            hangb.configure(relief="sunken")
            APP.gui.save_demod_cfg(None, hang=1)
        ReadCfg().read_cfg()

    @staticmethod
    def save_demod_cfg(tk_demod_cfg, **kwargs):
        """ Audio demodulation config window Save button actions. """
        if kwargs.get('lp_cut') is not None:
            APP.gui.changelpvalue(kwargs.get('lp_cut'))
            APP.gui.lowpass_scale.set(kwargs.get('lp_cut'))
        if kwargs.get('hp_cut') is not None:
            APP.gui.changehpvalue(kwargs.get('hp_cut'))
            APP.gui.highpass_scale.set(kwargs.get('hp_cut'))
        for key, value in kwargs.items():
            SaveCfg().save_cfg("demod", key, value)
            ReadCfg().read_cfg()
        if tk_demod_cfg is not None:
            tk_demod_cfg.destroy()

    @staticmethod
    def changelpvalue(lpvalue):
        """ Adapt the high pass slider according to moved low pass slider (should not be higher). """
        global LP_CUT
        # KiwiSDRStream().set_mod(mod='lsb', lc=0, hc=-500, freq=12345)
        if 'APP' in globals():
            APP.gui.lowpass_scale.configure(label="Low Pass Filter (" + str(lpvalue) + "Hz)")
            if APP.gui.lowpass_scale.get() >= APP.gui.highpass_scale.get():
                APP.gui.highpass_scale.set(APP.gui.lowpass_scale.get() + 10)
                LP_CUT = APP.gui.lowpass_scale.get()
            else:
                LP_CUT = APP.gui.lowpass_scale.get()
            return LP_CUT

    @staticmethod
    def changehpvalue(hpvalue):
        """ Adapt the low pass slider according to moved high pass slider (should not be lower). """
        global HP_CUT
        if 'APP' in globals():
            APP.gui.highpass_scale.configure(label="High Pass Filter (" + str(hpvalue) + "Hz)")
            if APP.gui.highpass_scale.get() <= APP.gui.lowpass_scale.get():
                APP.gui.lowpass_scale.set(APP.gui.highpass_scale.get() - 10)
                HP_CUT = APP.gui.highpass_scale.get()
            else:
                HP_CUT = APP.gui.highpass_scale.get()
            return HP_CUT

    @staticmethod
    def ctrla(event):
        """ Allow ctrl+A in frequency input textbox. """
        event.widget.select_range(0, 'end')
        event.widget.icursor('end')
        return 'break'

    @staticmethod
    def freq_focus(event):
        """ Adding Ctrl+F shortcut to focus the frequency input box. """
        APP.gui.freq_input.focus_set()
        APP.gui.freq_input.select_range(0, 'end')
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
    Enter a frequency and choose a modulation first

    Left click to start demodulating
    Right click to get node informations
    Get a real-time waterfall & SNR measurement with the Check SNR line
    Add/Remove nodes from favorite/blacklist with the appropriate button

    Map filtering is possible using the Map Settings menu

    Instant switch from node to node is possible using Left click on another icon

    """, width=1000, font="TkFixedFont 8", bg="white", anchor="center")
        help_menu.pack()

    @staticmethod
    def about():
        """ About menu text. """
        master = Tk()
        about_menu = Message(master, text="""
    Welcome to """ + VERSION + """

    The World map icons colors are static, click UPDATE button to get a fresh listing (please don't abuse)
    real-time KiwiSDR node informations are retrieved when node square icon is right-clicked on the map

    Thanks to Pierre Ynard (linkfanel) for the KiwiSDR network node listing + SNR used as source for GUI map update
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
        icon_slider = Scale(ICON_CFG, from_=1, to=5)
        icon_slider.place(x=10, y=0, width=200, height=100)
        icon_slider.configure(orient="horizontal", showvalue="1", resolution=1, label="")
        icon_slider.set(ICONSIZE)
        icon_save_button = Button(ICON_CFG, command=lambda *args: self.set_default_icon_size(icon_slider.get()))
        icon_save_button.place(x=220, y=20, height=20)
        icon_save_button.configure(text="Save")

    @staticmethod
    def set_default_icon_size(isize):
        """ Save choosed icon size to config file. """
        APP.gui.writelog("Icon size set to " + str(isize))
        SaveCfg().save_cfg("map", "iconsize", isize)
        ICON_CFG.destroy()
        APP.gui.redraw()

    def gradiant_change(self):
        """ Change SNR gradiant ratio window. """
        global GRAD_CFG
        GRAD_CFG = Tk()
        GRAD_CFG.geometry("280x50+50+50")
        GRAD_CFG.title('Default SNR gradiant ratio')
        icon_slider2 = Scale(GRAD_CFG, from_=1, to=50)
        icon_slider2.place(x=10, y=0, width=200, height=100)
        icon_slider2.configure(orient="horizontal", showvalue="1", resolution=1, label="")
        icon_slider2.set(GRAD)
        icon_save_button2 = Button(GRAD_CFG, command=lambda *args: self.set_default_gradiant(icon_slider2.get()))
        icon_save_button2.place(x=220, y=20, height=20)
        icon_save_button2.configure(text="Save")

    @staticmethod
    def set_default_gradiant(grad_val):
        """ Save choosed icon size to config file. """
        APP.gui.writelog("SNR gradiant set to " + str(grad_val))
        SaveCfg().save_cfg("guicolors", "grad", grad_val)
        GRAD_CFG.destroy()
        APP.gui.redraw()

    def threshold_change(self):
        """ Change SNR gradiant ratio window. """
        global THRES_CFG
        THRES_CFG = Tk()
        THRES_CFG.geometry("280x50+50+50")
        THRES_CFG.title('Black/White font color threshold')
        icon_slider3 = Scale(THRES_CFG, from_=1, to=255)
        icon_slider3.place(x=10, y=0, width=200, height=100)
        icon_slider3.configure(orient="horizontal", showvalue="1", resolution=1, label="")
        icon_slider3.set(THRES)
        icon_save_button2 = Button(THRES_CFG, command=lambda *args: self.set_font_threshold(icon_slider3.get()))
        icon_save_button2.place(x=220, y=20, height=20)
        icon_save_button2.configure(text="Save")

    @staticmethod
    def set_font_threshold(thres_val):
        """ Save Black/White font color threshold (in node menus) to config file. """
        APP.gui.writelog("Black/White font color threshold set to " + str(thres_val))
        SaveCfg().save_cfg("guicolors", "thres", thres_val)
        THRES_CFG.destroy()
        APP.gui.redraw()

    @staticmethod
    def color_change(value):
        """ Ask for a color and save to config file. """
        color_n = askcolor()
        color_n = color_n[1]
        if color_n:
            if value == 0:
                SaveCfg().save_cfg("map", "std", color_n)
                APP.gui.label01.configure(fg=color_n)
            if value == 1:
                SaveCfg().save_cfg("map", "fav", color_n)
                APP.gui.label02.configure(fg=color_n)
            if value == 2:
                SaveCfg().save_cfg("map", "blk", color_n)
                APP.gui.label03.configure(fg=color_n)
            if value == 4:
                SaveCfg().save_cfg("map", "hlt", color_n)
                APP.gui.writelog("Icon highlight color is now " + color_n)
            if value == 5:
                SaveCfg().save_cfg("guicolors", "main_b", color_n)
                APP.gui.writelog("GUI background color is now " + color_n)
                nums = ['0', '1', '2', '3', '4']
                chg_list = [APP.gui.ctrl_backgd, APP.gui.lowpass_scale, APP.gui.highpass_scale, APP.gui.label1,
                            APP.gui.label2]
                for x, l in zip(nums, chg_list):
                    l.configure(background=color_n)
                    l.configure(foreground=GuiCanvas.get_font_color(color_n))
                    SaveCfg().save_cfg("guicolors", "main_f", GuiCanvas.get_font_color(color_n))
            if value == 6:
                SaveCfg().save_cfg("guicolors", "cons_b", color_n)
                APP.gui.writelog("Console background color is now " + color_n)
                APP.gui.console_window.configure(bg=color_n)
            if value == 7:
                SaveCfg().save_cfg("guicolors", "cons_f", color_n)
                APP.gui.writelog("Console foreground color is now " + color_n)
                APP.gui.console_window.configure(fg=color_n)
        else:
            pass
        APP.gui.redraw()

    @staticmethod
    def choose_map():
        """ Change map menu and save to config file. """
        mapname = tkFileDialog.askopenfilename(initialdir="maps")
        if not mapname or not mapname.lower().endswith(('.png', '.jpg', '.jpeg')):
            tkMessageBox.showinfo("", message="Error, select png/jpg/jpeg files only.")
            mapname = "maps/directKiwi_map_grayscale_with_sea.jpg"
        SaveCfg().save_cfg("map", "file", "maps/" + os.path.split(mapname)[1])
        SaveCfg().save_cfg("map", "x0", str(b_box2[0]))
        SaveCfg().save_cfg("map", "y0", str(b_box2[1]))
        SaveCfg().save_cfg("map", "x1", str(b_box2[2]))
        SaveCfg().save_cfg("map", "y1", str(b_box2[3]))
        Restart().run()

    @staticmethod
    def set_map_position():
        """ Remember the map position and save to config file. """
        SaveCfg().save_cfg("map", "x0", str(b_box2[0]))
        SaveCfg().save_cfg("map", "y0", str(b_box2[1]))
        SaveCfg().save_cfg("map", "x1", str(b_box2[2]))
        SaveCfg().save_cfg("map", "y1", str(b_box2[3]))
        APP.gui.writelog("Default map position has been saved in config file")

    def runupdate(self):
        """ Run Web source availability check. """
        self.update_button.configure(state="disabled")
        # start the Check update thread
        CheckUpdate().start()

    @staticmethod
    def checkversion(source):
        """ Watch on github if a new version has been released (1st line of README.md parsed). """
        try:
            checkver = requests.get('https://raw.githubusercontent.com/llinkz/directKiwi/master/README.md', timeout=2)
            gitsrctext = checkver.text.split("\n")
            if float(gitsrctext[0][2:].split("v", 1)[1]) > float(VERSION.split("v", 1)[1][:4]):
                tkMessageBox.showinfo(title="", message=str(gitsrctext[0][2:]) + " released !")
            else:
                if source == "from_menu":
                    tkMessageBox.showinfo(title="", message="No update found.")
        except (ImportError, requests.RequestException):
            print("Unable to verify version information. Sorry.")


class MainW(Tk, object):
    """ Creating the Tk GUI design. """

    def __init__(self):
        Tk.__init__(self)
        Tk.option_add(self, '*Dialog.msg.font', 'TkFixedFont 7')
        self.gui = MainWindow(self)


def on_closing():
    """ Actions to perform when software is closed using the top-right check button. """
    if tkMessageBox.askokcancel("Quit", "Do you want to quit?"):
        try:  # to kill LISTEN MODE before quiting GUI
            os.kill(CLIENT_PID, signal.SIGTERM)
        except (NameError, OSError):
            pass
        os.kill(os.getpid(), signal.SIGTERM)
        APP.destroy()


if __name__ == '__main__':
    APP = MainW()
    APP.title(VERSION)
    APP.protocol("WM_DELETE_WINDOW", on_closing)
    APP.bind("<Control-f>", MainWindow.freq_focus)
    APP.mainloop()
