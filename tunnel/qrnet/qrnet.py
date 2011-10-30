#!/usr/bin/python

import sys
import os
import re
import time
import struct
import base64
import StringIO
import opencv
from opencv import highgui, adaptors
import qrencode
import zbar
from PIL import Image
import gtk
import gobject
import urllib
import socket
import subprocess
import Queue
import threading
import mutex

sys.path.append("../../../")
from ether2any import Ether2Any
from conf import Conf

mqueueMutex = threading.Lock()
squeueMutex = threading.Lock()
exqueue = Queue.Queue()

class QrDisplay(gtk.Window):
	def __init__(self, mqueue, squeue, displog, timeout=250):
		super(QrDisplay, self).__init__()
		
		self.timeout = timeout
		self.mqueue = mqueue
		self.squeue = squeue
		self.displog = displog
		
		self.fullscreen()
		self.qrimgPadding = 20
		(wx, wy) = self.getHackySize()
		
		# build up gui
		self.vbox = gtk.VBox(False, 0)
		self.qrimg = gtk.Image()
		self.qrimg.show()
		self.vbox.pack_start(self.qrimg, True, True, self.qrimgPadding)
		self.vbox.show()
		
		self.pbar = gtk.ProgressBar()
		self.pbar.show()
		self.vbox.pack_start(self.pbar, False, False, 0)
		
		self.add(self.vbox)
		
		# connect signals
		self.connect("destroy", self.quitGui)
		self.set_size_request(wx, wy)
		self.maximize()
		self.set_position(gtk.WIN_POS_CENTER)
		self.show()
		self.qrSet("")
		gobject.timeout_add(self.timeout, self.checkQueue)
	
	def quitGui(self, *args, **kwargs):
		exqueue.put(KeyboardInterrupt())
	
	def checkQueue(self):
		#print "Check queue...",
		mqueueMutex.acquire()
		if not self.mqueue.empty():
			print "new data available"
			bmsg = self.mqueue.get()
			self.qrSet(bmsg)
		mqueueMutex.release()
		#else:
		#	print "no new data available"
		
		# progress
		squeueMutex.acquire()
		if not self.squeue.empty():
			(frames, success) = self.squeue.get()
			if frames > 0:
				self.pbar.set_fraction(success/float(frames))
				self.pbar.set_text("%02d / %02d (%03.02f)" % (success, frames, success / float(frames) * 100.0)) 
			print frames, success
		squeueMutex.release()
		return True
		
	def getHackySize(self):
		""" Obtain current size of screen via xrandr. """
		#p = subprocess.Popen(["bash", "-c", 'xrandr|egrep "\*+"|egrep -o "[0-9]+x[0-9]+"'], stdout=subprocess.PIPE)
		p = subprocess.Popen('xrandr|egrep "\*+"|egrep -o "[0-9]+x[0-9]+"', stdout=subprocess.PIPE, shell=True)
		p.wait()
		(myout, myin) = p.communicate()
		return map(lambda x: int(x)-self.qrimgPadding, myout.strip().split("x"))
	
	def image2pixbuf(self, im):
		(a, b, c, d) = self.qrimg.get_allocation()
		# correct size, must be 1:1 (so select the smaller one)
		x = min(c-a, d-b)
		if(x < 10):
			x = 100
		imgSize = (x, x)
		im = im.resize(imgSize)
		file1 = StringIO.StringIO()  
		im.save(file1, "ppm")  
		contents = file1.getvalue()  
		file1.close()  
		loader = gtk.gdk.PixbufLoader("pnm")  
		loader.write(contents, len(contents))  
		pixbuf = loader.get_pixbuf()  
		loader.close()
		return pixbuf
	
	def qrSet(self, msg):
		""" Set content of displayed qr image. """
		if msg == None or msg == "":
			msg = "Katze"
		(qrVersion, qrSize, qrImg) = qrencode.encode(msg, 0)
		self.qrimg.set_from_pixbuf(self.image2pixbuf(qrImg))


class DisplayThread(threading.Thread):
	""" Thread that runs the GTK-GUI to display outgoing network qr codes. """
	def __init__(self, dev, mqueue, squeue, displog):
		threading.Thread.__init__(self)
		self.dev = dev
		self.quit = False
		self.qrdisplay = QrDisplay(mqueue, squeue, displog)
		self.mqueue = mqueue
		self.squeue = squeue
		self.displog = displog
		
	def run(self):
		self.displog.info("Display GTK Gui is up and running.")
		try:
			gtk.main()
		except Exception, e:
			exqueue.push(e)

class CamThread(threading.Thread):
	""" Captures images from a webcam and decodes them.

	Captures images from the first webcam it can find, decodes them
	and writes them to the interface. """
	def __init__(self, dev, squeue, camlog):
		threading.Thread.__init__(self)
		
		self.dev = dev
		self.squeue = squeue
		self.camlog = camlog
		
		self.frame = 0
		self.reportAfter = 20 # frames
		self.quit = False
		self.success = 0
		self.lastPacket = ""
		
		self.reader = highgui.cvCreateCameraCapture(Conf.get("camnum", 0))
		self.scanner = zbar.ImageScanner()
		self.scanner.parse_config('enable')
	
	def run(self):
		try:
			while not self.quit:
				frame = highgui.cvQueryFrame(self.reader)
				self.frame += 1
				
				frame = opencv.cvGetMat(frame)
				img = adaptors.Ipl2PIL(frame)
				width, height = img.size
				zimg = zbar.Image(width, height, 'Y800', img.convert("L").tostring())
				self.scanner.scan(zimg)
				data = None
				for symbol in zimg:
					data = symbol.data
					self.camlog.debug("Data is: %s" % data)
					self.success += 1
					# handle data
					if not self.lastPacket == data:
						self.lastPacket = data
						try:
							msg = base64.b64decode(data)
							(rawtime, packet) = (msg[0:8], msg[8:])
							ptime = struct.unpack("<d", rawtime)
							self.camlog.debug("Network packet! Heade (time) is %s" % (ptime,))
							self.dev.write(packet)
						except (base64.binascii.Error, TypeError):
							self.camlog.error("Base64 error - could not decode packet")
						except struct.error:
							self.camlog.error("Header error - could not extract header information")
					else:
						# packet is already known, discard
						pass

				# status report to gui
				if self.frame % self.reportAfter == 0:
					self.frame = self.success = 0
				
				squeueMutex.acquire()
				if self.squeue.qsize() > self.reportAfter/2:
					while not self.squeue.empty():
						self.squeue.get()
				# add new status code
				self.squeue.put((self.frame, self.success))
				squeueMutex.release()
		except Exception, e:
			exqueue.put(e)
			raise e
					

class QrNet(Ether2Any):
	pidlen = 16
	def __init__(self):
		# device
		Ether2Any.__init__(self, tap=True)
		self.qrlog = self.setupLogging("QrNet")
		self.mqueue = Queue.Queue()
		self.squeue = Queue.Queue()
		self.setTimeout(1)
		
		network = Conf.get("network", {'mtu': 400})
		self.packetDrop = Conf.get("packetDrop", 20)
		
		self.dev.ifconfig(**network)
		self.dev.up()
		
		# thread starting...
		gtk.gdk.threads_init()
		
		self.cam = CamThread(self.dev, self.squeue, self.setupLogging("CamThread"))
		self.cam.start()
		self.display = DisplayThread(self.dev, self.mqueue, self.squeue, self.setupLogging("DisplayThread"))
		self.display.start()
	
	def sendToNet(self, msg):
		# prepare data for queue && display
		self.qrlog.debug("Data from the device")
		
		# add acttime to generate "unique" images
		acttime = struct.pack("<d", time.time())
		bmsg = base64.b64encode(acttime + msg)
		self.qrlog.debug("==>" + bmsg)
		
		# add packet to queue, maybe drop packet
		mqueueMutex.acquire()
		if self.mqueue.qsize() < self.packetDrop:
			self.mqueue.put(bmsg)
		else:
			self.qrlog.debug("Dropping packet!")
		mqueueMutex.release()
	
	def callAfterSelect(self):
		# check queue for excetions
		if exqueue.qsize() > 0:
			ex = exqueue.get()
			raise ex
	
	def quit(self):
		self.display.quit = True
		self.cam.quit = True
		gtk.main_quit()

if __name__ == '__main__':
	try:
		qrnet = QrNet()
		qrnet.run()
	except KeyboardInterrupt:
		try:
			qrnet.quit()
		except NameError:
			pass
		sys.exit(0)
	except Exception, e:
		raise e
