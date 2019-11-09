#!/usr/bin/python
# -*- coding: utf-8 -*-
""" Here is the IS0KYB microkiwi_waterfall script, modified to use python instead of jupyther notebook. """

import numpy as np
import socket
import struct
import time
from datetime import datetime
import wsclient
import matplotlib.pyplot as plt

import mod_pywebsocket.common
from mod_pywebsocket.stream import Stream
from mod_pywebsocket.stream import StreamOptions

from optparse import OptionParser

parser = OptionParser()
parser.add_option("-f", "--file", dest="filename", type=str,
                  help="write waterfall data to binary FILE", metavar="FILE")
parser.add_option("-s", "--server", type=str,
                  help="server name", dest="server", default='127.0.0.1')
parser.add_option("-p", "--port", type=int,
                  help="port number", dest="port", default=8073)
parser.add_option("-l", "--length", type=int,
                  help="how many samples to draw from the server", dest="length", default=200)
parser.add_option("-z", "--zoom", type=int,
                  help="zoom factor", dest="zoom", default=0)
parser.add_option("-o", "--offset", type=int,
                  help="start frequency in kHz", dest="start", default=0)
parser.add_option("-v", "--verbose", type=int,
                  help="whether to print progress and debug info", dest="verbosity", default=0)

options = vars(parser.parse_args()[0])

if 'filename' in options:
    filename = options['filename']
else:
    filename = None

host = options['server']
port = options['port']
bins = 1024
zoom = options['zoom']
offset_khz = options['start']  # this is offset in kHz

full_span = 30000.0  # for a 30MHz kiwiSDR
if zoom > 0:
    span = full_span / 2. ** zoom
else:
    span = full_span

rbw = span / bins
if offset_khz > 0:
    # offset = (offset_khz - span / 2) / (full_span / bins) * 2 ** zoom * 1000.
    offset = (offset_khz + 100) / (full_span / bins) * 2 ** 4 * 1000.
    offset = max(0, offset)
else:
    offset = 0

center_freq = span / 2 + offset_khz

now = str(datetime.now())
header = [center_freq, span, now]
header_bin = struct.pack("II26s", *header)

try:
    mysocket = socket.socket()
    mysocket.connect((host, port))
except:
    print "Failed to connect, sleeping and reconnecting"
    exit()

uri = '/%d/%s' % (int(time.time()), 'W/F')
handshake = wsclient.ClientHandshakeProcessor(mysocket, host, port)
handshake.handshake(uri)

request = wsclient.ClientRequest(mysocket)
request.ws_version = mod_pywebsocket.common.VERSION_HYBI13

stream_option = StreamOptions()
stream_option.mask_send = True
stream_option.unmask_receive = False

mystream = Stream(request, stream_option)

# send a sequence of messages to the server, hardcoded for now
# max wf speed, no compression
msg_list = ['SET auth t=kiwi p=', 'SET zoom=%d start=%d' % (zoom, offset), 'SET maxdb=0 mindb=-100', 'SET wf_speed=4',
            'SET wf_comp=0']
for msg in msg_list:
    mystream.send_message(msg)
# number of samples to draw from server
length = options['length']
# create a numpy array to contain the waterfall data
wf_data = np.zeros((length, bins))
binary_wf_list = []
time = 0
while time < length:
    # receive one msg from server
    tmp = mystream.receive_message()
    if "W/F" in tmp:  # this is one waterfall line
        tmp = tmp[16:]  # remove some header from each msg
        print "received sample"
        if options['verbosity']:
            print time,
        # spectrum = np.array(struct.unpack('%dB'%len(tmp), tmp) ) # convert from binary data to uint8
        spectrum = np.ndarray(len(tmp), dtype='B', buffer=tmp)  # convert from binary data to uint8
        if filename:
            binary_wf_list.append(tmp)  # append binary data to be saved to file
        # wf_data[time, :] = spectrum-255 # mirror dBs
        wf_data[time, :] = spectrum
        wf_data[time, :] = -(255 - wf_data[time, :])  # dBm
        wf_data[time, :] = wf_data[time, :] - 13  # typical Kiwi wf cal
        time += 1
    else:  # this is chatter between client and server
        if "plot_width" in tmp:
            plot_width = tmp.rsplit("=")[1]
        pass

try:
    mystream.close_connection(mod_pywebsocket.common.STATUS_GOING_AWAY)
    mysocket.close()
except Exception as e:
    print "exception: %s" % e

avg_wf = np.mean(wf_data, axis=0)  # average over time
p95 = np.percentile(avg_wf, 95)
median = np.percentile(avg_wf, 50)
maxsig = np.max(wf_data)
minsig = np.min(wf_data)

print "SNR: %i dB [median: %i dB, p95: %i dB, high: %i dBm, low: %i dBm]" % (p95 - median, median, p95, maxsig, minsig)

if filename:
    with open(filename, "wb") as fd:
        fd.write(header_bin)  # write the header info at the top
        for line in binary_wf_list:
            fd.write(line)

with open("wf.bin", "rb") as fd:
    buff = fd.read()

header_len = 8 + 26  # 2 unsigned int for center_freq and span: 8 bytes PLUS 26 bytes for datetime

length = len(buff[header_len:])
n_t = length / bins

header = struct.unpack('2I26s', buff[:header_len])
data = struct.unpack('%dB' % length, buff[header_len:])

waterfall_array = np.reshape(np.array(data[:]), (n_t, bins))
waterfall_array -= 255

plt.figure(figsize=(14, 5))
plt.yticks(np.arange(0, 0, step=1))
plt.xlabel('MHz')
plt.xticks(np.linspace(0, bins, 31), np.linspace(0, 30, num=31, endpoint=True, dtype=int))
plt.pcolormesh(waterfall_array[:, 1:], vmin=minsig, vmax=maxsig)
plt.title("HF waterfall @ " + str(host) + " - [SNR: %i dB" % (p95 - median) + "]")
clb = plt.colorbar()
clb.ax.set_title('dBm')
plt.show()

