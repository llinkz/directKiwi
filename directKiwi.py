#!/usr/bin/python
# -*- coding: utf-8 -*-

import Tkinter as tk
from Tkinter import Menu
import ttk
import threading
import os
import signal
import time
import datetime
import subprocess
from subprocess import PIPE
import re
import pygeoip
import urllib
import socket
from tkColorChooser import askcolor
import tkMessageBox
import sys

VERSION = "directKiwi v3.63 by linkz"


class RunUpdate(threading.Thread):

    def __init__(self, parent=None):
        super(RunUpdate, self).__init__()
        self.parent = parent

    def run(self):
        global kiwi_nodenumber, kiwi_errors, kiwi_update, kiwi_names, kiwi_users, kiwi_users_max, kiwi_coords
        global kiwi_loc, kiwi_sw_version, kiwi_antenna, kiwi_uptime, kiwi_hostname, kiwi_geoipcountries
        try:
            urllib.URLopener().retrieve("http://kiwisdr.com/public/", "kiwisdr.com_public_.htm")  # dl listing source
            self.parent.writeupdatelog("[" + str(time.strftime('%H:%M.%S', time.gmtime())) + "] [UPDATE STARTED] -  ")
            kiwi_nodenumber = 0
            kiwi_errors = 0
            kiwi_update = []
            kiwi_names = []
            kiwi_users = []
            kiwi_users_max = []
            kiwi_coords = []
            kiwi_loc = []
            kiwi_sw_version = []
            kiwi_antenna = []
            kiwi_uptime = []
            kiwi_hostname = []
            kiwi_geoipcountries = []
            with open('kiwisdr.com_public_.htm', "r") as f:
                for line in f:  # parse the listing source html file, line after line, could be a better process, later
                    update = re.search(
                        r'(Monday, |Tuesday, |Wednesday, |Thursday, |Friday, |Saturday, |Sunday, )(.*) <br>', line)
                    name = re.search(r'<!-- name=(.*) -->', line)
                    users = re.search(r'<!-- users=(.*) -->', line)
                    users_max = re.search(r'<!-- users_max=(.*) -->', line)
                    # coords = re.search(r'<!-- gps=\(\D*(\-?\d+\.?\d+)\D*,\s?(\-?\d+\.?\d+).* -->', line)
                    loc = re.search(r'<!-- loc=(.*) -->', line)
                    sw_version = re.search(r'<!-- sw_version=KiwiSDR_v(.*) -->', line)
                    antenna = re.search(r'<!-- antenna=(.*) -->', line)
                    uptime = re.search(r'<!-- uptime=(.*) -->', line)
                    hostname = re.search(r'<a href=\'http://(.*)\' .*', line)  # (?!:)
                    # starting to construct the lists
                    if update:
                        kiwi_update.append(update.group(2))
                    if name:
                        kiwi_names.append(
                            name.group(1).decode('ascii', 'ignore').replace(".", "").replace(",", ""))
                    elif name is False:
                        kiwi_names.append('none')
                    if users:
                        kiwi_users.append(users.group(1))
                    elif users is False:
                        kiwi_users.append('x')
                    if users_max:
                        kiwi_users_max.append(users_max.group(1))
                    elif users_max is False:
                        kiwi_users_max.append('x')
                    # if coords:
                    #     kiwi_coords.append("[" + coords.group(1) + ", " + coords.group(2) + "]")
                    # elif coords is False:
                    kiwi_coords.append('[0,0]')
                    if loc:
                        kiwi_loc.append(loc.group(1).decode('ascii', 'ignore').replace(".", "").replace(",", " "))
                    elif loc is False:
                        kiwi_loc.append('none')
                    if sw_version:
                        kiwi_sw_version.append(sw_version.group(1))
                    elif kiwi_sw_version is False:
                        kiwi_sw_version.append('xxxxx')
                    if antenna:
                        kiwi_antenna.append(antenna.group(1).decode('ascii', 'ignore').replace(".", "").replace(",", " "))
                    elif antenna is False:
                        kiwi_antenna.append('none')
                    if uptime:
                        kiwi_uptime.append(datetime.timedelta(seconds=int(uptime.group(1))))
                    elif uptime is False:
                        kiwi_uptime.append('none')
                    if hostname:
                        kiwi_hostname.append(hostname.group(1))
                    else:
                        pass
            f.close()
            os.remove('kiwisdr.com_public_.htm')
            os.remove('directKiwi_server_list.db')
            with open('directKiwi_server_list.db', "w") as g:
                for names in kiwi_names:
                    kiwi_nodenumber += 1
                    g.write("%s'," % names)
                g.write("\n")
                for coord in kiwi_coords:
                    g.write("%s'," % coord)
                g.write("\n")
                for users in kiwi_users:
                    g.write("%s'," % users)
                g.write("\n")
                for users_max in kiwi_users_max:
                    g.write("%s'," % users_max)
                g.write("\n")
                for loc in kiwi_loc:
                    g.write("%s'," % loc)
                g.write("\n")
                for sw_version in kiwi_sw_version:
                    g.write("%s'," % sw_version)
                g.write("\n")
                for antenna in kiwi_antenna:
                    g.write("%s'," % antenna)
                g.write("\n")
                for uptime in kiwi_uptime:
                    g.write("%s'," % uptime)
                g.write("\n")
                for hostname in kiwi_hostname:
                    g.write("%s'," % hostname)
                g.write("\n")
                for hostname in kiwi_hostname:
                    if len(hostname.split(":", 1)[0]) != 0:
                        # time.sleep(10)
                        try:
                            ipcheck = pygeoip.GeoIP('GeoIP.dat').country_name_by_addr(
                                socket.gethostbyname(hostname.split(":", 1)[0]))
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(2)  # below is portcheck response check
                            result = sock.connect_ex((hostname.split(":", 1)[0], int(hostname.split(":", 1)[1])))
                            if result == 0:
                                self.parent.writeupdatelog(".")
                                self.parent.greenupdate()
                                # temporary deal with all xxx.proxy.kiwisdr.com hosts detected as from United States
                                if hostname.split(":", 1)[0] == "pu2per.proxy.kiwisdr.com":
                                    g.write("Brazil',")
                                elif hostname.split(":", 1)[0] == "hb9odp.proxy.kiwisdr.com":
                                    g.write("Switzerland',")
                                elif hostname.split(":", 1)[0] == "hbsdr.proxy.kiwisdr.com":
                                    g.write("China',")
                                elif hostname.split(":", 1)[0] == "kiwi.aprs.fi":
                                    g.write("Finland',")
                                elif hostname.split(":", 1)[0] == "g8nop.proxy.kiwisdr.com":
                                    g.write("United Kingdom',")
                                elif hostname.split(":", 1)[0] == "kongsdr.proxy.kiwisdr.com":
                                    g.write("Norway',")
                                elif hostname.split(":", 1)[0] == "paraguay.proxy.kiwisdr.com":
                                    g.write("Paraguay',")
                                elif hostname.split(":", 1)[0] == "julusdalen.proxy.kiwisdr.com":
                                    g.write("Norway',")
                                elif hostname.split(":", 1)[0] == "i1fqh.proxy.kiwisdr.com":
                                    g.write("Italy',")
                                elif hostname.split(":", 1)[0] == "sdrbris.proxy.kiwisdr.com":
                                    g.write("Australia',")
                                elif hostname.split(":", 1)[0] == "izh.proxy.kiwisdr.com":
                                    g.write("Russian Federation',")
                                elif hostname.split(":", 1)[0] == "ve3hls.proxy.kiwisdr.com":
                                    g.write("Canada',")
                                elif hostname.split(":", 1)[0] == "r3tio.proxy.kiwisdr.com":
                                    g.write("Russian Federation',")
                                elif hostname.split(":", 1)[0] == "irk.proxy.kiwisdr.com":
                                    g.write("Russian Federation',")
                                elif hostname.split(":", 1)[0] == "la4d.proxy.kiwisdr.com":
                                    g.write("Norway',")
                                elif hostname.split(":", 1)[0] == "khabsdr.proxy.kiwisdr.com":
                                    g.write("Russian Federation',")
                                elif hostname.split(":", 1)[0] == "kiwisdr.briata.org":
                                    g.write("Italia',")
                                elif hostname.split(":", 1)[0] == "sdr1.on1aff.be":
                                    g.write("Belgium',")
                                elif hostname.split(":", 1)[0] == "hb9odk.proxy.kiwisdr.com":
                                    g.write("Switzerland',")
                                elif hostname.split(":", 1)[0] == "informationsbyran.proxy.kiwisdr.com":
                                    g.write("Sweden',")
                                elif hostname.split(":", 1)[0] == "oz1bfm.proxy.kiwisdr.com":
                                    g.write("Denmark',")									
				else:
                                    g.write("%s'," % ipcheck)
                            else:
                                kiwi_errors += 1
                                g.write("%s'," % "unknown")
                                self.parent.redupdate()
                                self.parent.writeupdatelog("_")
                            sock.close()
                        except Exception:
                            kiwi_errors += 1
                            g.write("%s'," % "unknown")
                            self.parent.redupdate()
                            self.parent.writeupdatelog("*")
                    else:
                        kiwi_errors += 1
                        g.write("%s'," % "unknown")
                        self.parent.redupdate()
                        self.parent.writeupdatelog("*")
                g.write("\n")
                for update in kiwi_update:
                    g.write("%s" % update)
                g.write("\n")
                g.write("%s" % kiwi_errors)
            g.close()
            self.parent.writeupdatelog("\n")
            self.parent.writeupdatelog("[" + str(time.strftime('%H:%M.%S', time.gmtime())) + "] "
              "[UPDATE FINISHED] -  legend:     . = node is OK     * = host NOK     _ = port NOK (timeout=2sec)\n")
            self.parent.writeupdatelog("[" + str(time.strftime('%H:%M.%S', time.gmtime())) + "] [UPDATE FINISHED] -  "
              + str(kiwi_nodenumber) + " nodes found, but " + str(kiwi_errors) + " nodes are unreachable.\n")

            self.parent.writeupdatelog("[" + str(time.strftime('%H:%M.%S',
             time.gmtime())) + "] [UPDATE FINISHED] -  Local file \"directKiwi_server_list.db\" has been created.\n")
            executable = sys.executable
            args = sys.argv[:]
            args.insert(0, sys.executable)
            os.execvp(sys.executable, args)

        except Exception as dlerror:
            pass
            #self.parent.writelog("ERROR",
            #                    "Can't retrieve kiwisdr.com/public/ webpage : " + str(dlerror) + " - UPDATE aborted !")
            #self.parent.updatefail()


class StartKiwiSDR(threading.Thread):

    def __init__(self, parent=None):
        super(StartKiwiSDR, self).__init__()
        self.parent = parent

    def run(self):
        global kiwisdrclient_pid, threadstarted, dblclick, server_host, frequency, parent, line
        global server_port, modulation, lp_cut, hp_cut
        global autoagcactive, hang, managcgain, threshold, slope, decay
        self.parent.writelog("LOG",
                             "Node connection in progress...please wait for server response (Cancel button to abort)")
        proc = subprocess.Popen(
            ['python', 'KiwiSDRclient.py', '-s', str(server_host), '-p', str(server_port), '-f', str(frequency), '-m',
             str(modulation), '-L', str(lp_cut), '-H', str(hp_cut), '-g', str(autoagcactive), str(managcgain),
             str(hang), str(threshold), str(slope), str(decay)], stdout=PIPE, shell=False)
        kiwisdrclient_pid = proc.pid
        while True:
            line = proc.stdout.readline()
            if line != '':
                if "-" not in line and "array" not in line:
                    self.parent.writelog("NODE INFO", line.rstrip())  # KiwiSDRclient.py stdout (node parameters)
                if "sample_rate" in line:
                    threadstarted = True
                    dblclick = True
                    self.parent.connectionsucceed()
                if "-" in line and "array" not in line:  # RSSI int values, those are negative and between -120 and -10
                    self.parent.feedsmeter(int(line.rstrip()) + 120)  # sends RSSI value to feed the smeter
                if "Failed to connect" in line:
                    self.parent.writelog("NODE ERROR", "This KiwiSDR seems unreachable, check your parameters.")
                    threadstarted = False
                    if kiwisdrclient_pid:
                        os.kill(kiwisdrclient_pid, signal.SIGINT)
                        kiwisdrclient_pid = None
                        self.parent.writelog("LOG", "Node connection aborted....")
                        self.parent.connectionfailed()
                    time.sleep(0.5)
                    dblclick = False
                if "too_busy" in line:
                    self.parent.writelog("NODE ERROR", "This KiwiSDR is too busy, try again later.")
                    threadstarted = False
                    if kiwisdrclient_pid:
                        os.kill(kiwisdrclient_pid, signal.SIGINT)
                        kiwisdrclient_pid = None
                        self.parent.writelog("LOG", "Node connection aborted....")
                        self.parent.connectionfailed()
                    time.sleep(0.5)
                    dblclick = False
                    pass
                if "badp: 1" in line:
                    self.parent.writelog("NODE ERROR", "This KiwiSDR is protected by password, sorry.")
                    threadstarted = False
                    if kiwisdrclient_pid:
                        os.kill(kiwisdrclient_pid, signal.SIGINT)
                        kiwisdrclient_pid = None
                        self.parent.writelog("LOG", "Node connection aborted....")
                        self.parent.connectionfailed()
                    time.sleep(0.5)
                    dblclick = False
                if "down" in line:
                    self.parent.writelog("NODE ERROR", "This KiwiSDR is down for the moment, sorry.")
                    threadstarted = False
                    if kiwisdrclient_pid:
                        os.kill(kiwisdrclient_pid, signal.SIGINT)
                        kiwisdrclient_pid = None
                        self.parent.writelog("LOG", "Node connection aborted....")
                        self.parent.connectionfailed()
                    time.sleep(0.5)
                    dblclick = False
            else:
                break


class MainWindow(tk.Frame, object):

    def __init__(self):
        super(MainWindow, self).__init__()
        global kiwisdrclient_pid, threadstarted, frequency, server_info, server_host, server_port, modulation
        global main_pid, line, autoagcactive, kiwi_update, i, bgc, fgc, dfgc, lp_cut, hp_cut
        global treeviewtext, treeviewback, consoletext, consoleback, rootgeometry
        global defaultlowpassvalue, defaulthighpassvalue, defaultmodulation, defaultsortlisting
        global hang, managcgain, threshold, slope, decay, col1
        main_pid = os.getpid(); frequency = tk.DoubleVar(); server_info = tk.StringVar(); server_host = tk.StringVar()
        server_port = tk.IntVar(); modulation = tk.StringVar(); bgc = '#d9d9d9'; fgc = '#000000'; dfgc = '#a3a3a3'
        frequency = 10000; threadstarted = False; kiwisdrclient_pid = None; defaultlowpassvalue = '0'
        defaulthighpassvalue = '3600'; defaultsortlisting = 'Country'
        with open('directKiwi.cfg', "r") as c:
            configline = c.readlines()
            treeviewtext = configline[1].replace("\n", ""); treeviewback = configline[3].replace("\n", "")
            consoletext = configline[5].replace("\n", ""); consoleback = configline[7].replace("\n", "")
            rootgeometry = configline[9].replace("\n", ""); lp_cut = configline[11].replace("\n", "")
            hp_cut = configline[13].replace("\n", ""); defaultmodulation = configline[15].replace("\n", "")
            autoagcactive = configline[17].replace("\n", ""); hang = configline[19].replace("\n", "")
            managcgain = configline[21].replace("\n", ""); threshold = configline[23].replace("\n", "")
            slope = configline[25].replace("\n", ""); decay = configline[27].replace("\n", "")
            defaultsortlisting = configline[29].replace("\n", "")
        c.close()
        root.geometry(rootgeometry)  # root.geometry("1000x450+200+200") <= default tk window geometry
        root.title(VERSION)
        root.configure(background=bgc)

        self.master.title("directKiwi menu")  # building the top bar menus
        menubar = Menu(self.master)
        self.master.config(menu=menubar)
        filemenu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=filemenu)
        menubar.add_command(label="About", command=self.about)
        submenu = Menu(filemenu, tearoff=0)
        submenu1 = Menu(filemenu, tearoff=0)
        submenu1.add_command(label="Listing text", command=self.listingtext)
        submenu1.add_command(label="Listing background", command=self.listingbackground)
        submenu1.add_command(label="Console text", command=self.consoletext)
        submenu1.add_command(label="Console background", command=self.consolebackground)
        submenu.add_cascade(label='Default', menu=submenu1, underline=0)
        submenu2 = Menu(filemenu, tearoff=0)
        submenu21 = Menu(filemenu, tearoff=0)
        submenu21.add_command(label="Low pass filter", command=self.defaultlowpass)
        submenu21.add_command(label="High pass filter", command=self.defaulthighpass)
        submenu2.add_cascade(label='Default', menu=submenu21, underline=0)
        submenu3 = Menu(filemenu, tearoff=0)
        submenu31 = Menu(filemenu, tearoff=0)
        submenu31.add_command(label="USB", command=lambda *args: self.defaultmodulation(0))
        submenu31.add_command(label="LSB", command=lambda *args: self.defaultmodulation(1))
        submenu31.add_command(label="AM", command=lambda *args: self.defaultmodulation(2))
        submenu31.add_command(label="CW", command=lambda *args: self.defaultmodulation(3))
        submenu31.add_command(label="NFM", command=lambda *args: self.defaultmodulation(4))
        submenu3.add_cascade(label='Default', menu=submenu31, underline=0)
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
        submenu5 = Menu(filemenu, tearoff=0)
        submenu51 = Menu(filemenu, tearoff=0)
        submenu51.add_cascade(label="by Country", command=lambda *args: self.default_sort_listing(1))
        submenu51.add_cascade(label='by Name', command=lambda *args: self.default_sort_listing(2))
        submenu51.add_command(label="by Location", command=lambda *args: self.default_sort_listing(3))
        submenu51.add_command(label="by Antenna", command=lambda *args: self.default_sort_listing(4))
        submenu51.add_command(label="by Host", command=lambda *args: self.default_sort_listing(5))
        submenu51.add_command(label="by Version", command=lambda *args: self.default_sort_listing(6))
        submenu51.add_command(label="by Users", command=lambda *args: self.default_sort_listing(7))
        submenu51.add_command(label="by Uptime", command=lambda *args: self.default_sort_listing(8))
        submenu5.add_cascade(label='Default', menu=submenu51, underline=0)
        filemenu.add_cascade(label='Colors', menu=submenu, underline=0)
        filemenu.add_cascade(label='Bandwidth', menu=submenu2, underline=0)
        filemenu.add_cascade(label='Modulation', menu=submenu3, underline=0)
        filemenu.add_cascade(label='Gain control', menu=submenu4, underline=0)
        filemenu.add_cascade(label='Sort listing', menu=submenu5, underline=0)
        filemenu.add_command(label='Save config', command=self.saveconfig)

        self.Button1 = tk.Button(root)  # disconnect
        self.Button1.place(relx=0.010, rely=0.02, height=24, relwidth=0.070)
        self.Button1.configure(activebackground=bgc, activeforeground=fgc, background=bgc, disabledforeground=dfgc,
                               foreground=fgc, highlightbackground=bgc, highlightcolor=fgc, pady="0",
                               text="Disconnect", command=self.clickstop, state="disabled")

        self.Entry1 = tk.Entry(root, textvariable=frequency)  # frequency
        self.Entry1.place(relx=0.09, rely=0.02, relheight=0.05, relwidth=0.22)
        self.Entry1.configure(background="white", disabledforeground=dfgc, font="TkFixedFont", foreground=fgc,
                              insertbackground=fgc, width=214)
        self.Entry1.insert(0, "Enter Frequency here (kHz)")
        self.Entry1.bind('<FocusIn>', self.clickfreq)

        self.Button2 = tk.Button(root)  # connect to
        self.Button2.place(relx=0.32, rely=0.02, height=24, relwidth=0.073)
        self.Button2.configure(activebackground=bgc, activeforeground=fgc, background=bgc, disabledforeground=dfgc,
                               foreground=fgc, highlightbackground=bgc, highlightcolor=fgc, pady="0",
                               text="Connect to:", state="disabled", command=self.startkiwimanual)

        self.Entry2 = tk.Entry(root, textvariable=server_info)  # host:port or ip:port
        self.Entry2.place(relx=0.4, rely=0.02, relheight=0.05, relwidth=0.24)
        self.Entry2.configure(background="white", disabledforeground=dfgc, font="TkFixedFont", foreground=fgc,
                              insertbackground=fgc, width=234)
        self.Entry2.insert(0, "Enter manual \"HOST:PORT\" here")
        self.Entry2.bind('<FocusIn>', self.clickhost)
        # self.Entry2.insert("end", "192.168.1.103:8073")  # for testing purpose at home

        self.TCombobox1 = ttk.Combobox(root, state="readonly")  # modulation combobox
        self.TCombobox1.place(relx=0.65, rely=0.02, relheight=0.05, relwidth=0.055)
        self.TCombobox1.configure(font="TkTextFont", values=["USB", "LSB", "AM", "CW", "NFM"])
        self.TCombobox1.current(defaultmodulation)
        self.TCombobox1.bind("<<ComboboxSelected>>", self.modulationchoice)

        self.TCombobox2 = ttk.Combobox(root, state="readonly")  # agc/mgc combobox
        self.TCombobox2.place(relx=0.71, rely=0.02, relheight=0.05, relwidth=0.055)
        self.TCombobox2.configure(font="TkTextFont", values=["MGC", "AGC"])
        self.TCombobox2.current(autoagcactive)
        self.TCombobox2.bind("<<ComboboxSelected>>", self.mgcsetting)

        if autoagcactive == "0":
            gain_slider0 = 'raised'; gain_slider1 = 'normal'; display_label1 = 'normal'
            display_label1_color = fgc
        else:
            gain_slider0 = 'flat'; gain_slider1 = 'disabled'; display_label1 = 'normal'
            display_label1_color = bgc
        self.Scale1 = tk.Scale(root, to=120, command=self.mgcset)  # gain scale
        self.Scale1.place(relx=0.77, rely=0.02, relwidth=0.19, relheight=0.0, height=23)
        self.Scale1.configure(activebackground=bgc, background=bgc, font="TkTextFont", foreground=fgc,
                              highlightbackground=bgc, highlightcolor=fgc, orient="horizontal", showvalue="0",
                              troughcolor=bgc, resolution=1, sliderrelief=gain_slider0, state=gain_slider1)
        self.Scale1.set(managcgain)

        self.label1 = tk.Label(root)
        self.label1.place(relx=0.96, rely=0.02, relwidth=0.2, relheight=0.0, height=23)
        self.label1.configure(background=bgc, foreground=display_label1_color, relief="flat", anchor='w',
                              text=managcgain + "dB", state=display_label1)

        self.TProgressbar1 = ttk.Progressbar(root)  # s-meter
        self.TProgressbar1.place(x=10, rely=0.1, relwidth=0.97, relheight=0.0, height=22)
        self.TProgressbar1.configure(length="970", maximum="110", value='0')
        # s-meter scale and placement
        smetertext = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', '+10', '+20', '+30', '+40', '+50', '+60']
        smeterplaces = ['0.01', '0.046', '0.097', '0.151', '0.205', '0.256', '0.310', '0.361', '0.415', '0.496',
                        '0.585', '0.669', '0.7565', '0.8455', '0.9315']
        s = 0
        while s < len(smetertext):
            self.label = tk.Label(root)
            self.label.place(relx=smeterplaces[s], rely=0.15, height=14, relheight=0.0, relwidth=0.97)
            self.label.configure(background=bgc, foreground=fgc, relief="flat", anchor='w', text=smetertext[s])
            s += 1

        self.Scale2 = tk.Scale(root, from_=0, to=6000)  # low pass filter scale
        self.Scale2.place(relx=0.01, rely=0.20, relwidth=0.98, relheight=2.0, height=23)
        self.Scale2.set(lp_cut)
        self.Scale2.configure(activebackground=bgc, background=bgc, font="TkTextFont", foreground=fgc,
                              highlightbackground=bgc, highlightcolor=fgc, length="970", orient="horizontal",
                              showvalue="0", troughcolor=bgc, resolution=10,
                              label="Low Pass Filter (0Hz)", command=self.changelpvalue)

        self.Scale3 = tk.Scale(root, from_=0, to=6000)  # high pass filter scale
        self.Scale3.place(relx=0.01, rely=0.30, relwidth=0.98, relheight=2.0, height=23)
        self.Scale3.set(hp_cut)
        self.Scale3.configure(activebackground=bgc, background=bgc, font="TkTextFont", foreground=fgc,
                              highlightbackground=bgc, highlightcolor=fgc, length="970", orient="horizontal",
                              showvalue="0", troughcolor=bgc, resolution=10,
                              label="High Pass Filter (3600Hz)", command=self.changehpvalue)

        self.treeview1 = ttk.Treeview(root)  # node listing
        ttk.Style().configure("Treeview", fieldbackground=fgc, background=treeviewback, foreground=treeviewtext)
        self.treeview1.place(relx=0.01, rely=0.42, relheight=0.27, relwidth=0.97)
        self.treeview1.configure(columns="Country Name Location Antenna Host Version Users Uptime")
        col1 = ['#0', 'Country', 'Name', 'Location', 'Antenna', 'Host', 'Version', 'Users', 'Uptime']
        col2 = ['', 'Country', 'Node Name', 'Node Location', 'Antenna', 'Host', 'Ver.', 'Users', 'Uptime']
        col3 = ['0', '80', '150', '130', '130', '150', '20', '6', '60']
        col4 = ['0', '1', '1', '1', '1', '1', '1', '1', '1']
        t = 0
        while t < len(col1):
            self.treeview1.heading(col1[t], text=col2[t], anchor="w")
            self.treeview1.column(col1[t], width=col3[t], minwidth="20", stretch=col4[t], anchor="w")
            t += 1

        with open('directKiwi_server_list.db') as h:  # fill the node listing with db file
            i = 0
            q = 1
            lines = h.readlines()
            kiwi_names = lines[0].split("',"); kiwi_users = lines[2].split("',"); kiwi_users_max = lines[3].split("',")
            kiwi_locations = lines[4].split("',"); kiwi_versions = lines[5].split("',")
            kiwi_antennae = lines[6].split("',"); kiwi_uptimes = lines[7].split("',"); kiwi_hosts = lines[8].split("',")
            kiwi_geoipcountries = lines[9].split("',"); kiwi_update = lines[10]; kiwi_errors = lines[11]
            nb_nodes = len(kiwi_versions)
            while i < nb_nodes - int(kiwi_errors):
                if kiwi_geoipcountries[i] != "unknown":
                    self.treeview1.insert("", 0, q, text="", values=(
                    kiwi_geoipcountries[i], kiwi_names[i], kiwi_locations[i], kiwi_antennae[i], kiwi_hosts[i],
                    kiwi_versions[i], kiwi_users[i] + "/" + kiwi_users_max[i], kiwi_uptimes[i]))
                i += 1
                q += 1
        h.close()
        columns = ("Country", "Name", "Location", "Antenna", "Host", "Version", "Users", "Uptime")
        for col in columns:
            self.treeview1.heading(col, text=col,
                                   command=lambda _col=col: treeview_sort_column(self.treeview1, _col, False))

        self.treeview1.bind("<Double-1>", self.startkiwi)  # start a connect when double click a line in treeview

        def treeview_sort_column(tv, col, reverse):  # node list sorting routine
            lis = [(tv.set(k, col), k) for k in tv.get_children('')]
            lis.sort(reverse=reverse)
            for index, (val, k) in enumerate(lis):
                tv.move(k, '', index)
            tv.heading(col, command=lambda: treeview_sort_column(tv, col, not reverse))

        treeview_sort_column(self.treeview1, defaultsortlisting, 0)  # autosort at program start
        vsb = ttk.Scrollbar(root, orient="vertical", command=self.treeview1.yview)  # adding scrollbar to listing
        vsb.place(relx=0.98, rely=0.42, relheight=0.27, relwidth=0.02)
        self.treeview1.configure(yscrollcommand=vsb.set)

        self.Button3 = tk.Button(root, command=self.runupdate)  # update button
        self.Button3.place(relx=0.01, rely=0.698, height=21, relwidth=0.97)
        self.Button3.configure(activebackground=bgc, activeforeground=fgc, background=bgc, disabledforeground=dfgc,
                               foreground=fgc, highlightbackground=bgc, highlightcolor=fgc, pady="0",
                               text="CLICK HERE TO UPDATE")
        root.title(VERSION + " - " + str(i) + " KiwiSDRs are available.")

        self.Text2 = tk.Text(root)  # console window
        self.Text2.place(relx=0.01, rely=0.75, relheight=0.24, relwidth=0.97)
        self.Text2.configure(background=consoleback, font="TkTextFont", foreground=consoletext, highlightbackground=bgc,
                             highlightcolor=fgc, insertbackground=fgc, selectbackground="#c4c4c4",
                             selectforeground=fgc, undo="1", width=970, wrap="word")
        self.writelog("WELCOME", "This is " + VERSION + " (ounaid@gmail.com), a GUI written for python 2.7 / Tk")
        self.writelog("HOW TO", "First type a frequency, choose Modulation, Low Pass & High Pass, AGC or MGC then "
                                "double-click on a line to connect")
        self.writelog("HOW TO", "or type hostname & port in the top right box to connect to a specific KiwiSDR host"
                                ", syntaxes are HOST:PORT or IP:PORT")
        self.writelog("UPDATE INFO", "Update the KiwiSDR node listing with the dedicated button "
                                     "(source is http://kiwisdr.com/public) - Process may take some time.")
        self.writelog("UPDATE INFO",
                      "Locations of nodes are found using GeoIP and a port check routine runs during update. ")
        self.writelog("DB INFO", "directKiwi_server_list.db has " + str(nb_nodes) + " KiwiSDRs listed but " + str(
            kiwi_errors) + " were detected unreachable during last update.. (" + str(
            kiwi_update.replace("\n", "")) + ")")

        vsb2 = ttk.Scrollbar(root, orient="vertical", command=self.Text2.yview)  # adding scrollbar to console
        vsb2.place(relx=0.98, rely=0.75, relheight=0.24, relwidth=0.02)
        self.Text2.configure(yscrollcommand=vsb2.set)

    # -------------------------------------------------MENUS-------------------------------------------------------
    @staticmethod
    def about():  # about menu
        tkMessageBox.showinfo(title="About", message="This is " + VERSION + " (GUI using python 2.7 and Tk)." + """

Project webpage on http://81.93.247.141/~linkz/directKiwi/

This code has been written and released under the "do what the f$ck you want with it" license.

bug, reports and features request : ounaid@gmail.com
        """)

    def saveconfig(self):  # save config menu
        global treeviewtext, treeviewback, consoletext, consoleback, defaultlowpassvalue, defaulthighpassvalue
        global defaultmodulation, autoagcactive, hang, managcgain, threshold, slope, decay, defaultsortlisting
        os.remove('directKiwi.cfg')
        with open('directKiwi.cfg', "w") as u:
            u.write("Default Listing Text Color\n%s\n" % treeviewtext)
            u.write("Default Listing Background Color\n%s\n" % treeviewback)
            u.write("Default Console Text Color\n%s\n" % consoletext)
            u.write("Default Console Background Color\n%s\n" % consoleback)
            u.write("Default Window Geometry [width]x[height]+[left position]+[top position]\n%s\n" % root.geometry())
            u.write("Default Low Pass Filter (in Hz)\n%s\n" % defaultlowpassvalue)
            u.write("Default High Pass Filter (in Hz)\n%s\n" % defaulthighpassvalue)
            u.write("Default Modulation (0:USB 1:LSB 2:AM 3:CW 4:NFM)\n%s\n" % defaultmodulation)
            u.write("Default AGC/MGC (1:AGC 0:MGC)\n%s\n" % autoagcactive)
            u.write("Default AGC Hang (0/1)\n%s\n" % hang)
            u.write("Default gain (in MGC mode)\n%s\n" % managcgain)
            u.write("Default threshold (in AGC mode)\n%s\n" % threshold)
            u.write("Default slope (in AGC mode)\n%s\n" % slope)
            u.write("Default decay (in AGC mode)\n%s\n" % decay)
            u.write("Default sort (Country/Name/Location/Antenna/Host/Version/Users/Uptime)\n%s\n" % defaultsortlisting)
        u.close()
        self.writelog("STATUS", "Configuration settings saved.")

    @staticmethod
    def listingtext():  # node listing foreground color choice menu
        global treeviewtext
        color = askcolor()
        ttk.Style().configure("Treeview", foreground=color[1])
        treeviewtext = color[1]

    @staticmethod
    def listingbackground():  # node listing background color choice menu
        global treeviewback
        color = askcolor()
        ttk.Style().configure("Treeview", background=color[1])
        treeviewback = color[1]

    def consoletext(self):  # console foreground color choice menu
        global consoletext
        color = askcolor()
        self.Text2.configure(foreground=color[1])
        consoletext = color[1]

    def consolebackground(self):  # console background color choice menu
        global consoleback
        color = askcolor()
        self.Text2.configure(background=color[1])
        consoleback = color[1]

    def defaultlowpass(self):  # low pass filter default menu
        global lp_cut, topL
        topL = tk.Tk()
        topL.geometry(
            "280x50+%d+%d" % (int(root.geometry().split("+", 2)[1]) + 50, int(root.geometry().split("+", 2)[2]) + 50))
        topL.title('Default low pass filter (in Hz)')
        low_pass_slider = tk.Scale(topL, from_=0, to=6000)
        low_pass_slider.place(x=10, y=0, width=200, height=100)
        low_pass_slider.configure(orient="horizontal", showvalue="1", resolution=100, label="")
        low_pass_slider.set(lp_cut)
        low_pass_button = tk.Button(topL, command=lambda *args: self.setdefaultlowpass(low_pass_slider.get()))
        low_pass_button.place(x=220, y=20, height=20)
        low_pass_button.configure(text="Apply")

    @staticmethod
    def setdefaultlowpass(lowvalue):
        global defaultlowpassvalue, topL
        defaultlowpassvalue = lowvalue
        topL.destroy()

    def defaulthighpass(self):  # high pass filter default menu
        global hp_cut, topH
        topH = tk.Tk()
        topH.geometry(
            "280x50+%d+%d" % (int(root.geometry().split("+", 2)[1]) + 50, int(root.geometry().split("+", 2)[2]) + 50))
        topH.title('Default high pass filter (in Hz)')
        high_pass_slider = tk.Scale(topH, from_=0, to=6000)
        high_pass_slider.place(x=10, y=0, width=200, height=100)
        high_pass_slider.configure(orient="horizontal", showvalue="1", resolution=100, label="")
        high_pass_slider.set(hp_cut)
        high_pass_button = tk.Button(topH, command=lambda *args: self.setdefaulthighpass(high_pass_slider.get()))
        high_pass_button.place(x=220, y=20, height=20)
        high_pass_button.configure(text="Apply")

    @staticmethod
    def setdefaulthighpass(highvalue):
        global defaulthighpassvalue, topH
        defaulthighpassvalue = highvalue
        topH.destroy()

    @staticmethod
    def defaultmodulation(modul):
        global defaultmodulation
        defaultmodulation = modul

    @staticmethod
    def default_agc(agcset):
        global autoagcactive
        autoagcactive = agcset

    @staticmethod
    def default_agc_hang(agchang):
        global hang
        hang = agchang

    def default_agc_gain(self):
        global managcgain, topG
        topG = tk.Tk()
        topG.geometry(
            "280x50+%d+%d" % (int(root.geometry().split("+", 2)[1]) + 50, int(root.geometry().split("+", 2)[2]) + 50))
        topG.title('Default gain (in MGC mode)')
        agc_gain_slider = tk.Scale(topG, from_=0, to=120)
        agc_gain_slider.place(x=10, y=0, width=200, height=100)
        agc_gain_slider.configure(orient="horizontal", showvalue="1", resolution=1, label="")
        agc_gain_slider.set(managcgain)
        agc_gain_button = tk.Button(topG, command=lambda *args: self.set_default_agc_gain(agc_gain_slider.get()))
        agc_gain_button.place(x=220, y=20, height=20)
        agc_gain_button.configure(text="Apply")

    @staticmethod
    def set_default_agc_gain(gainvalue):
        global managcgain, topG
        managcgain = gainvalue
        topG.destroy()

    def default_agc_threshold(self):
        global threshold, topT
        topT = tk.Tk()
        topT.geometry(
            "280x50+%d+%d" % (int(root.geometry().split("+", 2)[1]) + 50, int(root.geometry().split("+", 2)[2]) + 50))
        topT.title('Default threshold (in AGC mode)')
        threshold_slider = tk.Scale(topT, from_=-130, to=0)
        threshold_slider.place(x=10, y=0, width=200, height=100)
        threshold_slider.configure(orient="horizontal", showvalue="1", resolution=1, label="")
        threshold_slider.set(threshold)
        threshold_button = tk.Button(topT, command=lambda *args: self.set_default_agc_thres(threshold_slider.get()))
        threshold_button.place(x=220, y=20, height=20)
        threshold_button.configure(text="Apply")

    @staticmethod
    def set_default_agc_thres(thresvalue):
        global threshold, topT
        threshold = thresvalue
        topT.destroy()

    def default_agc_slope(self):
        global slope, topS
        topS = tk.Tk()
        topS.geometry(
            "280x50+%d+%d" % (int(root.geometry().split("+", 2)[1]) + 50, int(root.geometry().split("+", 2)[2]) + 50))
        topS.title('Default slope (in AGC mode)')
        slope_slider = tk.Scale(topS, from_=0, to=10)
        slope_slider.place(x=10, y=0, width=200, height=100)
        slope_slider.configure(orient="horizontal", showvalue="1", resolution=1, label="")
        slope_slider.set(slope)
        slope_button = tk.Button(topS, command=lambda *args: self.set_default_agc_slope(slope_slider.get()))
        slope_button.place(x=220, y=20, height=20)
        slope_button.configure(text="Apply")

    @staticmethod
    def set_default_agc_slope(slopevalue):
        global slope, topS
        slope = slopevalue
        topS.destroy()

    def default_agc_decay(self):
        global decay, topD
        topD = tk.Tk()
        topD.geometry(
            "280x50+%d+%d" % (int(root.geometry().split("+", 2)[1]) + 50, int(root.geometry().split("+", 2)[2]) + 50))
        topD.title('Default decay (in AGC mode)')
        decay_slider = tk.Scale(topD, from_=20, to=5000)
        decay_slider.place(x=10, y=0, width=200, height=100)
        decay_slider.configure(orient="horizontal", showvalue="1", resolution=10, label="")
        decay_slider.set(decay)
        decay_button = tk.Button(topD, command=lambda *args: self.set_default_agc_decay(decay_slider.get()))
        decay_button.place(x=220, y=20, height=20)
        decay_button.configure(text="Apply")

    @staticmethod
    def set_default_agc_decay(decayvalue):
        global decay, topD
        decay = decayvalue
        topD.destroy()

    @staticmethod
    def default_sort_listing(column):
        global col1, defaultsortlisting
        defaultsortlisting = col1[column]

    # -------------------------------------------------LOGGING------------------------------------------------------

    def writelog(self, type, msg):  # the main console log text feed
        self.Text2.insert('end -1 lines',
                          "[" + str(time.strftime('%H:%M.%S', time.gmtime())) + "] [" + type + "] - " + msg + "\n")
        time.sleep(0.01)
        self.Text2.see('end')

    def writeupdatelog(self, msg):  # the main console log text feed when update routine processes (different syntax)
        self.Text2.insert('end', msg)
        self.Text2.see('end')

    # -------------------------------------------------UPDATE-------------------------------------------------------

    def redupdate(self):  # set update button background color to red when an error occurs
        self.Button3.configure(background="#FF0000")
        time.sleep(0.05)
        self.Button3.configure(background="black")

    def greenupdate(self):  # set update button background color to green when host is fine
        self.Button3.configure(background="#00FF00")
        time.sleep(0.05)
        self.Button3.configure(background="black")

    def runupdate(self):  # if UPDATE button is pushed
        self.Button3.configure(state="disabled")  # disable UPDATE button
        self.Button3.configure(background="black", foreground="black", text="")
        RunUpdate(self).start()  # start the update thread

    def updatefail(self):  # when UPDATE is failed (ex: no public webpage available)
        self.Button3.configure(activebackground=bgc, activeforeground=fgc, background=bgc, disabledforeground=dfgc,
                               foreground=fgc, highlightbackground=bgc, highlightcolor=fgc, pady="0",
                               text="CLICK HERE TO UPDATE", state='normal')

    def updatedone(self):  # when UPDATE is done with success
        map(self.treeview1.delete, self.treeview1.get_children())  # purge the node listing
        time.sleep(0.5)
        with open('directKiwi_server_list.db') as h:  # redraw the node listing with updated db
            i = 0
            lines = h.readlines()
            kiwi_names = lines[0].split("',")
            kiwi_users = lines[2].split("',")
            kiwi_users_max = lines[3].split("',")
            kiwi_locations = lines[4].split("',")
            kiwi_versions = lines[5].split("',")
            kiwi_antennae = lines[6].split("',")
            kiwi_uptimes = lines[7].split("',")
            kiwi_hosts = lines[8].split("',")
            kiwi_geoipcountries = lines[9].split("',")
            kiwi_update = lines[10]
            kiwi_errors = lines[11]
            nb_nodes = len(kiwi_versions) - 1
            while i < nb_nodes - int(kiwi_errors):
                i += 1
                if kiwi_geoipcountries[i] != "unknown":
                    self.treeview1.insert("", 0, "", text="", values=(
                        kiwi_geoipcountries[i], kiwi_names[i], kiwi_locations[i], kiwi_antennae[i], kiwi_hosts[i],
                        kiwi_versions[i], kiwi_users[i] + "/" + kiwi_users_max[i], kiwi_uptimes[i]))
        h.close()
        self.Button3.configure(activebackground=bgc, activeforeground=fgc, background=bgc, disabledforeground=dfgc,
                               foreground=fgc, highlightbackground=bgc, highlightcolor=fgc, pady="0",
                               text="CLICK HERE TO UPDATE", state='normal')

    # ---------------------------------------------------MAIN-------------------------------------------------------

    def feedsmeter(self, rssi):  # as mentionned, feed the s-meter progress bar with RSSI values from socket
        self.TProgressbar1["value"] = rssi

    def startkiwi(self, event):  # actions when you double click on a listing line
        global frequency, server_host, server_port, server_info, modulation, lp_cut, hp_cut, threadstarted
        global dblclick, autoagcactive, managcgain
        if threadstarted and dblclick:
            self.writelog("STATUS", "New node connection in progress.")
            dblclick = False
            os.kill(kiwisdrclient_pid, signal.SIGINT)
            time.sleep(0.2)
            self.startkiwi(self)
        else:
            item = self.treeview1.selection()[0]
            server_host = str(str(self.treeview1.item(item, "values")[4]).split(":")[0])  # parse for hostname
            modulation = str(self.TCombobox1.get())  # get choosen modulation
            try:
                server_port = str(str(self.treeview1.item(item, "values")[4]).split(":")[1])  # parse for port
            except Exception as porterror:
                self.writelog("ERROR", "This node is unavailable ! [" + porterror + "]")
                threadstarted = False; dblclick = False
            if self.Entry1.get() == 'Enter Frequency here (kHz)':
                self.writelog("ERROR", "Enter frequency first !")
                threadstarted = False; dblclick = False
            elif self.Entry1.get() == '' or float(self.Entry1.get()) < 0 or float(self.Entry1.get()) > 30000:
                self.writelog("ERROR", "Check frequency !")
                threadstarted = False; dblclick = False
            else:
                frequency = str(float(self.Entry1.get()))
                if modulation == "LSB":
                    lp_cut = str(0 - self.Scale3.get()); hp_cut = str(0 - self.Scale2.get())
                elif modulation == "AM":
                    lp_cut = str("-5000"); hp_cut = str("5000")
                elif modulation == "CW":
                    lp_cut = str("900"); hp_cut = str("1100"); frequency = str(float(self.Entry1.get()) - 1)
                else:
                    lp_cut = str(self.Scale2.get()); hp_cut = str(self.Scale3.get())
                self.Button1.configure(text="Cancel", state="normal")  # enable the Disconnect button
                self.Button2.configure(state="disabled")  # disable the manual connect button if connected to a node
                self.Button3.configure(state="disabled")  # disable the UPDATE button if connected to a node
                self.TCombobox1.configure(state="disabled")  # disable the modulation listbox if connected to a node
                self.TCombobox2.configure(state="disabled")  # disable the agc/mgc listbox if connected to a node
                self.Scale1.configure(sliderrelief="flat", state="disabled")  # disable the AGC slider if connected
                self.Scale2.configure(sliderrelief="flat", state="disabled")  # disable the LP slider if connected
                self.Scale3.configure(sliderrelief="flat", state="disabled")  # disable the HP slider if connected
                if autoagcactive == '1':
                    root.title("Connected to " + str(server_host) + ":" + str(server_port) + " - " + str(
                        frequency) + "kHz " + (str(modulation.upper())) + " " + str(
                        int(hp_cut) - int(lp_cut)) + "Hz (AGC on)")
                else:
                    root.title("Connected to " + str(server_host) + ":" + str(server_port) + " - " + str(
                        frequency) + "kHz " + (str(modulation.upper())) + " " + str(
                        int(hp_cut) - int(lp_cut)) + "Hz (MGC set at " + str(managcgain) + "dB)")
                StartKiwiSDR(self).start()

    def startkiwimanual(self):  # actions when you click on Connect to:
        global frequency, server_host, server_port, server_info, modulation, lp_cut, hp_cut, managcgain, threadstarted
        global autoagcactive, kiwisdrclient_pid
        if self.Entry2.get() != "":
            server_host = str(str(self.Entry2.get().split(":")[0]))  # parse for hostname
            server_port = str(int(self.Entry2.get().split(":")[1]))  # parse for port
            modulation = str(self.TCombobox1.get())  # get choosen modulation
            if self.Entry1.get() == 'Enter Frequency here (kHz)' or self.Entry1.get() == '' or float(
                    self.Entry1.get()) < 0 or float(self.Entry1.get()) > 30000:  # freq
                self.writelog("ERROR", "Check frequency !")
            else:
                if threadstarted:
                    self.writelog("STATUS", "New node connection in progress.")
                    os.kill(kiwisdrclient_pid, signal.SIGINT)
                    time.sleep(0.2)
                    StartKiwiSDR(self).start()
                else:
                    frequency = str(float(self.Entry1.get()))
                    if modulation == "LSB":
                        lp_cut = str(0 - self.Scale3.get()); hp_cut = str(0 - self.Scale2.get())
                    elif modulation == "AM":
                        lp_cut = str("-5000"); hp_cut = str("5000")
                    elif modulation == "CW":
                        lp_cut = str("900"); hp_cut = str("1100"); frequency = str(float(self.Entry1.get()) - 1)
                    else:
                        lp_cut = str(self.Scale2.get()); hp_cut = str(self.Scale3.get())
                    self.Button1.configure(state="normal")  # enable the Disconnect button if connected to a node
                    self.Button2.configure(state="disabled")  # disable the manual connect button if connected to a node
                    self.Button3.configure(state="disabled")  # disable the UPDATE button if connected to a node
                    self.TCombobox1.configure(state="disabled")  # disable the modulation listbox if connected to a node
                    self.TCombobox2.configure(state="disabled")  # disable the agc/mgc listbox if connected to a node
                    self.Scale1.configure(sliderrelief="flat", state="disabled")  # disable the AGC slider if connected
                    self.Scale2.configure(sliderrelief="flat", state="disabled")  # disable the LP slider if connected
                    self.Scale3.configure(sliderrelief="flat", state="disabled")  # disable the HP slider if connected
                    if autoagcactive == '1':
                        root.title(
                            "Connected to " + str(server_host) + ":" + str(server_port) + " - " + str(frequency)
                            + "kHz " + (str(modulation.upper())) + " " + str(int(hp_cut) - int(lp_cut)) + "Hz (AGC on)")
                    else:
                        root.title("Connected to " + str(server_host) + ":" + str(server_port) + " - " + str(
                            frequency) + "kHz " + (str(modulation.upper())) + " " + str(
                            int(hp_cut) - int(lp_cut)) + "Hz (MGC set at " + str(managcgain) + "dB)")
                    StartKiwiSDR(self).start()  # start the connect thread

    def clickstop(self):  # actions when you click the Disconnect button
        global kiwisdrclient_pid, threadstarted, i
        self.TProgressbar1["value"] = 0  # reset s-meter
        root.title(VERSION + " - " + str(i) + " KiwiSDRs are available.")  # put top title back
        self.TCombobox1.configure(state="normal")  # enable the modulation listbox if not connected
        self.TCombobox2.configure(state="normal")  # enable the agc/mgc listbox if not connected
        self.Button1.configure(text="Disconnect", state="disabled")  # disable the Disconnect button if not connected
        if self.Entry2.get() == "" or self.Entry2.get() == 'Enter manual "HOST:PORT" here':
            self.Button2.configure(state="disabled")
        else:
            self.Button2.configure(state="normal")
        self.Button3.configure(state="normal")  # enable the UPDATE button if no connected
        if self.TCombobox2.get() == "MGC":
            self.Scale1.configure(sliderrelief="raised", state="normal")  # enable the MGC slider if not connected
        self.Scale2.configure(sliderrelief="raised", state="normal")  # enable the LP slider if not connected
        self.Scale3.configure(sliderrelief="raised", state="normal")  # enable the HP slider if not connected
        os.kill(kiwisdrclient_pid, signal.SIGINT)  # kill the StartKiwiSDR() thread
        kiwisdrclient_pid = None  # unset the kiwisdrclient PID variable
        if threadstarted:
            self.writelog("STATUS", "Node disconnected.")
        else:
            self.writelog("INFO", "Connection has been aborted by user...")
        threadstarted = False

    def mgcset(self, value):
        global managcgain
        if self.TCombobox2.get() == "MGC":
            managcgain = self.Scale1.get()
            self.label1.configure(text=str(managcgain) + "dB")

    def mgcsetting(self, ggg):
        global autoagcactive, managcgain
        if self.TCombobox2.get() == "MGC":
            self.writelog("STATUS", "MGC is active, range is from 0dB to 120dB, default=" + str(managcgain) + "dB.")
            self.Scale1.configure(sliderrelief="raised", state="normal")
            self.label1.configure(foreground=fgc)
            time.sleep(0.05)
            self.Scale1.set(managcgain)
            managcgain = self.Scale1.get()
            autoagcactive = '0'
        else:
            self.writelog("STATUS", "AGC is active.")
            self.Scale1.configure(sliderrelief="flat", state="disabled")
            self.label1.configure(foreground=bgc)
            autoagcactive = '1'

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

    def modulationchoice(self, m):  # affects only the main window apparance, real-time
        global modulation
        modulation = self.TCombobox1.get()
        if modulation == "CW":
            self.Scale2.configure(sliderrelief="flat", state="disabled")  # Hides the LP/HP sliders when CW
            self.Scale3.configure(sliderrelief="flat", state="disabled")
            self.writelog("STATUS", "With CW modulation, frequency offset=-1kHz / BW=200Hz / AF center=1000Hz.")
        elif modulation == "AM":
            self.Scale2.configure(sliderrelief="flat", state="disabled")  # Hides the LP/HP sliders when AM
            self.Scale3.configure(sliderrelief="flat", state="disabled")
            self.writelog("STATUS", "With AM modulation the BW default is now set to 10kHz.")
        else:
            self.Scale2.configure(sliderrelief="raised", state="normal")
            self.Scale3.configure(sliderrelief="raised", state="normal")
            time.sleep(0.01)
            self.Text2.see('end')

    def clickfreq(self, ff):  # when you click in frequency input box
        self.Entry1.delete(0, 'end')

    def clickhost(self, hh):  # when you click on hostname:port input box
        self.Entry2.delete(0, 'end')
        self.Button2.configure(state="normal")

    def connectionsucceed(self):  # change the 1st button text
        self.Button1.configure(text="Disconnect", state="normal")

    def connectionfailed(self):  # do some things when a connection can't be performed ok
        self.Button1.configure(text="Disconnect", state="disabled")  # disable  button if connection has failed
        self.Button3.configure(state="normal")  # enable the UPDATE button
        self.TCombobox1.configure(state="normal")  # enable the modulation listbox
        self.TCombobox2.configure(state="normal")  # enable the agc/mgc listbox
        self.Scale2.configure(sliderrelief="raised", state="normal")  # enable the LP slider
        self.Scale3.configure(sliderrelief="raised", state="normal")  # enable the HP slider


if __name__ == '__main__':
    root = tk.Tk()
    frame = MainWindow()
    root.mainloop()
