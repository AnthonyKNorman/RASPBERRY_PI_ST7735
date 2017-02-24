# Derived from - the library by Tony DiCola
# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import numbers
import time
import RPi.GPIO as GPIO
import spidev as SPI

from PIL import Image, ImageDraw, ImageFont


#constants
DELAY = 0x80
ST7735_TFTWIDTH = 128
ST7735_TFTHEIGHT = 160

ST7735_NOP = 0x00
ST7735_SWRESET = 0x01
ST7735_RDDID = 0x04
ST7735_RDDST = 0x09

ST7735_SLPIN = 0x10
ST7735_SLPOUT = 0x11
ST7735_PTLON = 0x12
ST7735_NORON = 0x13

ST7735_INVOFF = 0x20
ST7735_INVON = 0x21
ST7735_DISPOFF = 0x28
ST7735_DISPON = 0x29
ST7735_CASET = 0x2A
ST7735_RASET = 0x2B
ST7735_RAMWR = 0x2C
ST7735_RAMRD = 0x2E

ST7735_PTLAR = 0x30
ST7735_COLMOD = 0x3A
ST7735_MADCTL = 0x36

ST7735_FRMCTR1 = 0xB1
ST7735_FRMCTR2 = 0xB2
ST7735_FRMCTR3 = 0xB3
ST7735_INVCTR = 0xB4
ST7735_DISSET5 = 0xB6

ST7735_PWCTR1 = 0xC0
ST7735_PWCTR2 = 0xC1
ST7735_PWCTR3 = 0xC2
ST7735_PWCTR4 = 0xC3
ST7735_PWCTR5 = 0xC4
ST7735_VMCTR1 = 0xC5

ST7735_RDID1 = 0xDA
ST7735_RDID2 = 0xDB
ST7735_RDID3 = 0xDC
ST7735_RDID4 = 0xDD

ST7735_PWCTR6 = 0xFC

ST7735_GMCTRP1 = 0xE0
ST7735_GMCTRN1 = 0xE1

# for the rotation definition
ST7735_MADCTL_MY = 0x80
ST7735_MADCTL_MX = 0x40
ST7735_MADCTL_MV = 0x20
ST7735_MADCTL_ML = 0x10
ST7735_MADCTL_RGB = 0x00
ST7735_MADCTL_BGR = 0x08
ST7735_MADCTL_MH = 0x04

def color565(r,g,b):
	"""Convert red, green, blue components to a 16-bit 565 RGB value. Components
	should be values 0 to 255.
	"""
	# r, g, b = rgb
	return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def color_rgb(color):
	"""Convert 565 color format to rgb - return tuple"""
	r = (color >> 8) & 0xf8
	g = ((color >> 5) & 0x3f) << 2
	b = (color & 0x1f) << 3
	return (r,g,b)

class ST7735(object):
	"""Representation of an ST7735 TFT LCD."""

	def __init__(self, dc, rst, offset=0, c_mode='RGB'):
		"""Create an instance of the display using SPI communication.  Must
		provide the GPIO pin number for the D/C pin and the SPI driver.  Can
		optionally provide the GPIO pin number for the reset pin as the rst
		parameter.
		"""
		self._dc = dc
		self._rst = rst
		self._spi = spi=SPI.SpiDev()
		self._gpio = GPIO
		self.width = ST7735_TFTWIDTH
		self.height = ST7735_TFTHEIGHT
		self._gpio.setmode(GPIO.BCM)
		# Set DC as output.
		self._gpio.setup(dc, GPIO.OUT)
		# Setup reset as output (if provided).
		if rst is not None:
		    self._gpio.setup(rst, GPIO.OUT)
			
		# Set SPI to mode 0, MSB first.
		spi.open(0,0)
		spi.mode = 0
		spi.max_speed_hz = 32000000

		# Create an image buffer.
		self.buffer = bytearray(self.width*self.height*2)
		self._row = 0
		self._col = 0
		self._color = 0
		self._bground = 0xf100
		self._font = ImageFont.truetype('/home/pi/python/OpenSans-Regular.ttf', 60)
		if c_mode == 'RGB':
			self._color_mode = ST7735_MADCTL_RGB
		else:
			self._color_mode = ST7735_MADCTL_BGR


	def send(self, data, is_data=True, chunk_size=4096):
		"""Write a byte or array of bytes to the display. Is_data parameter
		controls if byte should be interpreted as display data (True) or command
		data (False).  Chunk_size is an optional size of bytes to write in a
		single SPI transaction, with a default of 4096.
		"""
		# Set DC low for command, high for data.
		self._gpio.output(self._dc, is_data)
		# Convert scalar argument to list so either can be passed as parameter.
		if isinstance(data, numbers.Number):
		    data = [data & 0xFF]
		# Write data a chunk at a time.
		for start in range(0, len(data), chunk_size):
		    end = min(start+chunk_size, len(data))
		    self._spi.writebytes(data[start:end])

	def command(self, data):
		"""Write a byte or array of bytes to the display as command data."""
		self.send(data, False)

	def data(self, data):
		"""Write a byte or array of bytes to the display as display data."""
		self.send(data, True)

	def reset(self):
		"""Reset the display, if reset pin is connected."""
		if self._rst is not None:
		    self._gpio.output(self._rst, GPIO.HIGH)
		    time.sleep(0.005)
		    self._gpio.output(self._rst, GPIO.LOW)
		    time.sleep(0.02)
		    self._gpio.output(self._rst, GPIO.HIGH)
		    time.sleep(0.150)

	def _init(self):
		commands = bytearray([            # Initialization commands for 7735B screens
				ST7735_SWRESET,   DELAY,  #  1: Software reset, 0 args, w/delay
				  150,                    #     150 ms delay
				ST7735_SLPOUT ,   DELAY,  #  2: Out of sleep mode, 0 args, w/delay
				  255,                    #     500 ms delay
				ST7735_FRMCTR1, 3      ,  #  3: Frame rate ctrl - normal mode, 3 args:
				  0x01, 0x2C, 0x2D,       #     Rate = fosc/(1x2+40) * (LINE+2C+2D)
				ST7735_FRMCTR2, 3      ,  #  4: Frame rate control - idle mode, 3 args:
				  0x01, 0x2C, 0x2D,       #     Rate = fosc/(1x2+40) * (LINE+2C+2D)
				ST7735_FRMCTR3, 6      ,  #  5: Frame rate ctrl - partial mode, 6 args:
				  0x01, 0x2C, 0x2D,       #     Dot inversion mode
				  0x01, 0x2C, 0x2D,       #     Line inversion mode
				ST7735_INVCTR , 1      ,  #  6: Display inversion ctrl, 1 arg, no delay:
				  0x07,                   #     No inversion
				ST7735_PWCTR1 , 3      ,  #  7: Power control, 3 args, no delay:
				  0xA2,
				  0x02,                   #     -4.6V
				  0x84,                   #     AUTO mode
				ST7735_PWCTR2 , 1      ,  #  8: Power control, 1 arg, no delay:
				  0xC5,                   #     VGH25 = 2.4C VGSEL = -10 VGH = 3 * AVDD
				ST7735_PWCTR3 , 2      ,  #  9: Power control, 2 args, no delay:
				  0x0A,                   #     Opamp current small
				  0x00,                   #     Boost frequency
				ST7735_PWCTR4 , 2      ,  # 10: Power control, 2 args, no delay:
				  0x8A,                   #     BCLK/2, Opamp current small & Medium low
				  0x2A,  
				ST7735_PWCTR5 , 2      ,  # 11: Power control, 2 args, no delay:
				  0x8A, 0xEE,
				ST7735_VMCTR1 , 1      ,  # 12: Power control, 1 arg, no delay:
				  0x0E,
				ST7735_INVOFF , 0      ,  # 13: Don't invert display, no args, no delay
				ST7735_MADCTL , 1      ,  # 14: Memory access control (directions), 1 arg:
				  0xC8,                   #     row addr/col addr, bottom to top refresh
				ST7735_COLMOD , 1      ,  # 15: set color mode, 1 arg, no delay:
				  0x05,                   #     16-bit color
				ST7735_CASET  , 4      ,  #  1: Column addr set, 4 args, no delay:
				  0x00, 0x00,             #     XSTART = 0
				  0x00, 0x7F,             #     XEND = 127
				ST7735_RASET  , 4      ,  #  2: Row addr set, 4 args, no delay:
				  0x00, 0x00,             #     XSTART = 0
				  0x00, 0x9F,             #     XEND = 159
				ST7735_GMCTRP1, 16      , #  1: Magical unicorn dust, 16 args, no delay:
				  0x02, 0x1c, 0x07, 0x12,
				  0x37, 0x32, 0x29, 0x2d,
				  0x29, 0x25, 0x2B, 0x39,
				  0x00, 0x01, 0x03, 0x10,
				ST7735_GMCTRN1, 16      , #  2: Sparkles and rainbows, 16 args, no delay:
				  0x03, 0x1d, 0x07, 0x06,
				  0x2E, 0x2C, 0x29, 0x2D,
				  0x2E, 0x2E, 0x37, 0x3F,
				  0x00, 0x00, 0x02, 0x10,
				ST7735_NORON  ,    DELAY, #  3: Normal display on, no args, w/delay
				  10,                     #     10 ms delay
				ST7735_DISPON ,    DELAY, #  4: Main screen turn on, no args w/delay
				  100,                    #     100 ms delay
				ST7735_MADCTL, 1	,	  # change MADCTL color filter
				  0xC0|self._color_mode
		])                  
					  
		argcount = 0
		cmd = 1
		delay = 0
		for c in commands:
			if argcount == 0:				# no arguments collected
				if delay:					# if a delay flagged this is delay value
					if c == 255:			# if delay is 255ms make it 500ms
						c = 500
					time.sleep(c/100)
					delay = 0
				else:
					if cmd == 1:					# need to send command byte
						self.command(c)			# send coommand
						cmd = 0					# clear flag to show command sent
					else:
						argcount = c & (0xff ^ DELAY)	# Clear delay bit and get arguments
						delay = c & DELAY		# set if delay required
						cmd = 1					# flag command now complete
			else:							# arguments to send
				self.data(c)				# send argument
				argcount -= 1				# decrement the counter
		
	def begin(self):
		"""Initialize the display.  Should be called once before other calls that
		interact with the display are called.
		"""
		self.reset()
		self._init()

	def set_window(self, x0=0, y0=0, x1=None, y1=None):
		"""Set the pixel address window for proceeding drawing commands. x0 and
		x1 should define the minimum and maximum x pixel bounds.  y0 and y1
		should define the minimum and maximum y pixel bound.  If no parameters
		are specified the default will be to update the entire display from 0,0
		to 239,319.
		"""
		if x1 is None:
			x1 = self.width-1
		if y1 is None:
			y1 = self.height-1
		self.command(ST7735_CASET)		# Column addr set
		self.data(x0 >> 8)
		self.data(x0)				    # XSTART
		self.data(x1 >> 8)
		self.data(x1)				    # XEND
		self.command(ST7735_RASET)		# Row addr set
		self.data(y0 >> 8)
		self.data(y0)				    # YSTART
		self.data(y1 >> 8)
		self.data(y1)                    # YEND
		self.command(ST7735_RAMWR)        # write to RAM

		
	def pixel(self, x, y, color):
		"""Set an individual pixel to color"""
		if(x < 0) or (x >= self.width) or (y < 0) or (y >= self.height):
			return
		self.set_window(x,y,x+1,y+1)
		b=[color>>8, color & 0xff]
		self.data(b)
		
	def draw_block(self,x,y,w,h,color):
		"""Draw a solid block of color"""
		if((x >= self.width) or (y >= self.height)):
			return
		if (x + w - 1) >= self.width:
			w = self.width  - x
		if (y + h - 1) >= self.height:
			h = self.height - y
		self.set_window(x,y,x+w-1,y+h-1);
		b=[color>>8, color & 0xff]*w*h
		self.data(b)

	def draw_bmp(self,x,y,w,h,buff):
		"""Draw the contents of buff on the screen"""
		if((x >= self.width) or (y >= self.height)):
			return
		if (x + w - 1) >= self.width:
			w = self.width  - x
		if (y + h - 1) >= self.height:
			h = self.height - y

		self.set_window(x,y,x+w-1,y+h-1);
		self.data(buff)

	def fill_screen(self,color):
		"""Fill the whole screen with color"""
		self.draw_block(0,0,self.width,self.height,color)
		
	def p_char(self, ch):
		"""Print a single char at the location determined by globals row and color
			row and col will be auto incremented to wrap horizontally and vertically"""
		fp = (ord(ch)-0x20) * 5
		f = open('/home/pi/python/lib/font5x7.fnt','rb')
		f.seek(fp)
		b = f.read(5)
		char_buf = bytearray(b)
		char_buf.extend([0])

		# make 8x6 image
		char_image = []
		for bit in range(8):
			for x in range (6):
				if ((char_buf[x]>>bit) & 1)>0:
					char_image.extend([self._color >> 8])
					char_image.extend([self._color & 0xff])
				else:
					char_image.extend([self._bground >> 8])
					char_image.extend([self._bground & 0xff])
		x = self._col*6+1
		y = self._row*8+1
		
		self.set_window(x,y,x+5,y+7)
		self.data(char_image)
				
		self._col += 1
		if (self._col>30):
			self._col = 0
			self._row += 1
			if (self._row>40):
				self._row = 0

	def p_string(self, str):
		"""Print a string at the location determined by row and char"""
		for ch in (str):
			self.p_char(ch)
				
	def p_image(self, x, y, img):
		img = img.convert('RGB')
		w, h = img.size
		z = img.getdata()
		img_buf = []
		for pixel in (z):
			r,g,b = pixel
			rgb = color565(r,g,b)
			img_buf.extend([rgb >> 8])
			img_buf.extend([rgb & 0xff])
		self.draw_bmp(x,y,w,h,img_buf)
		
	def text(self, text, align='left', angle=0):
		# make a new square image the size of the largest
		# dislay dimension to support rotated text
		limit = max(self.height,self.width)
		img = Image.new('RGB', (limit, limit), color_rgb(self._bground))
		# make the draw object
		draw = ImageDraw.Draw(img)
		# get the width and height of the text image
		width, height = draw.textsize(text, font=self._font)
		# draw the text into the image
		draw.text((0,0),text,font=self._font,fill=color_rgb(self._color))
		# crop the image to the size of the text
		img=img.crop((0,0,width,height))
		# rotate the image
		img = img.rotate(angle)
		# return the image object and the width and height
		return img, width, height
			
	def set_rotation(self, m):
		self.command(ST7735_MADCTL)
		rotation = m % 4 # can't be higher than 3
		if rotation == 0:
			self.data(ST7735_MADCTL_MX | ST7735_MADCTL_MY | self._color_mode)
			self._width  = ST7735_TFTWIDTH
			self._height = ST7735_TFTHEIGHT
		elif rotation == 1:
			self.data(ST7735_MADCTL_MY | ST7735_MADCTL_MV | self._color_mode)
			self._width  = ST7735_TFTHEIGHT
			self._height = ST7735_TFTWIDTH
		elif rotation == 2:
			self.data(self._color_mode)
			self._width  = ST7735_TFTWIDTH
			self._height = ST7735_TFTHEIGHT
		elif rotation == 3:
			self.data(ST7735_MADCTL_MX | ST7735_MADCTL_MV | self._color_mode)
			self._width  = ST7735_TFTHEIGHT
			self._height = ST7735_TFTWIDTH

