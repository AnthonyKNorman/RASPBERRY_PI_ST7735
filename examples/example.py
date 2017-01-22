import time
import encoder

enc = encoder.encoder(max = 240, min = 120, step = 1)

while 1:
	# raw value is 8 x actual
	# take down to a 30 to 60 integer rage
	# then divide by 2 to give 0.5 step accuracy
	val = float(int(enc.my_val/4))/2
	print (val, enc.last_a1, enc.last_b1)
	time.sleep(.5)
