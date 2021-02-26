import sys, os, time, datetime
from pynput import mouse
import mss, mss.tools
import numpy, cv2

save_file = "./Boris.data"
screens_folder = "./screens/"
auto_save_frequency = 10 # auto save every n attempts
wait_delay = 1 # initial wait delay in ms, will be adjusted dynamically to hit fps target
target_fps = 10 # 10 for level selecting, 20 when doing attempts
downscale_resolution = (200,150) # as low as 40,30 has worked
level_select_screen_wait = 4 # secs to stay at level select screen to end session/change level
level_match_threshold = 0.88

# font stuff
font = cv2.FONT_HERSHEY_SIMPLEX 
fontScale = 1
thickness = 2
color_paused = (255,255,0) # cyan
color_running = (0,252,124) # bright green
color_inactive = (105,105,105) # grey
color_regular = (255,255,255) # white
color_flash = (0,0,255) # red


# save format is:
# level name=attempts=time in seconds
def save_data(level, attempts, time): # level = str, attempts = int, time = float
	# read old data
	levels_db = []
	attempts_db = []
	times_db = []

	time = round(time,3) # 3 should be plenty

	if os.path.isfile(save_file):
		f = open(save_file, "r")
		lines = f.readlines()
		f.close()
		for line in lines:
			levels_db.append(line.split("=")[0].rstrip())
			attempts_db.append(line.split("=")[1].rstrip())
			times_db.append(line.split("=")[2].rstrip())

	if level not in levels_db:
		levels_db.append(level)
		attempts_db.append(attempts)
		times_db.append(time)
	else:
		# modify db with new data
		index = levels_db.index(level)
		levels_db[index] = level # this line is not needed...
		attempts_db[index] = attempts
		times_db[index] = time	

	# save
	f = open(save_file, "w")
	for l in sorted(levels_db): # sort so file is in alphabetical order
		index = levels_db.index(l)
		line = l + "=" + str(attempts_db[index]) + "=" + str(times_db[index]) + "\n"
		f.write(line)
	f.close()

	print("Saved", level, "with", str(attempts) + " attempts, " + display_time(time), "time")

def load_data(level): # level = str, returns int (attempts) and float (time), 0 and 0.0 if not found
	if not os.path.isfile(save_file):
		print("No save data found:", save_file)
		return {"attempts": 0, "time": 0.0}

	levels_db = []
	attempts_db = []
	times_db = []

	f = open(save_file, "r")
	lines = f.readlines()
	f.close()

	for line in lines:
		levels_db.append(line.split("=")[0].rstrip())
		attempts_db.append( line.split("=")[1].rstrip() )
		times_db.append( line.split("=")[2].rstrip() )

	if level in levels_db:
		index = levels_db.index(level)
		attempts = int(attempts_db[index])
		time = float(times_db[index])
		print("Level previously played, attempts:", attempts, ", time:", display_time(time))
		return {"attempts": attempts, "time": time}
	else:
		print("Level not played before")
		return {"attempts": 0, "time": 0.0}

def compare_l2_norm(source, capture):
	# https://github.com/Toufool/Auto-Split/blob/master/src/compare.py
	error = cv2.norm(source, capture, cv2.NORM_L2)
	max_error = (source.size ** 0.5) * 255
	return 1 - (error/max_error)

def screenshotRegion(l,t,w,h):
	with mss.mss() as sct:
		region = {'top': t, 'left': l, 'width': w, 'height': h}
		ss = sct.grab(region)
		img = numpy.array(ss)
		return img

def display_time(in_secs): # in: seconds (preferably as float), out: string similar to HH:MM:SS.XXX
	h = int(in_secs // 3600)
	m = int(in_secs % 3600 // 60)
	s = int(in_secs % 3600 % 60)
	ms = str( float ( in_secs % 1 ) ).split(".")[1]
	#         ^^^^^ because we sometimes get a 0 in here (not 0.0)
	
	output = ""

	if h > 0: # H:MM:SS
		output = output + str(h) + ":"
		output = output + str(m).zfill(2) + ":"
		output = output + str(s).zfill(2)
	elif m > 0: # M:SS.X
		output = output + str(m) + ":"
		output = output + str(s).zfill(2)
		output = output + "." + ms[0:1]
	else: # S.XX
		output = output + str(s)
		output = output + "." + ms[0:2].zfill(2)

	return output

def percentage(fl):
	return str(round(fl*100, 1)) + "%"


coordsTopLeft = False
coordsBottomRight = False

def on_click(x, y, button, pressed):
	global coordsTopLeft
	global coordsBottomRight
	if pressed:
		#print(x,y)
		if not coordsTopLeft:
			coordsTopLeft = x,y
			return x,y
		elif not coordsBottomRight:
			coordsBottomRight =  x,y
			return x,y
		elif coordsTopLeft and coordsBottomRight:
			mouse.Listener.stop

####################################### starts here #############################################

## figure out screen region
listener = mouse.Listener(on_click=on_click)
listener.start()

tl_printed = False
br_printed = False

# this is sketchy af
while not coordsTopLeft:
	if not tl_printed:
		print('Click top-left corner of game capture')
		tl_printed = True
print("Topleft corner:", coordsTopLeft)

while not coordsBottomRight:
	if not br_printed:
		print('Click bottom-right corner of game capture')
		br_printed = True
print("Bottom right corner:", coordsBottomRight)

mouse.Listener.stop # is this necessary?

# easier names for the coords
pfLeft = coordsTopLeft[1]
pfTop = coordsTopLeft[0]
pfWidth = coordsBottomRight[0]-coordsTopLeft[0]
pfHeight = coordsBottomRight[1]-coordsTopLeft[1]

# prepare images (greyscale and scale them)
print("Preparing comparison images...")
black_frame = cv2.resize(cv2.cvtColor(numpy.zeros((400,300,3), numpy.uint8), cv2.COLOR_BGR2GRAY), downscale_resolution) # we create a black frame (numpy.zeros) to use for the black comparison
level_select_frame_jp = cv2.resize(cv2.cvtColor(cv2.imread("screens/Level Select JP.png"), cv2.COLOR_BGR2GRAY), downscale_resolution)
level_select_frame_en = cv2.resize(cv2.cvtColor(cv2.imread("screens/Level Select EN.png"), cv2.COLOR_BGR2GRAY), downscale_resolution)
difficulty_frame = cv2.resize(cv2.cvtColor(cv2.imread("screens/Diff.png"), cv2.COLOR_BGR2GRAY), downscale_resolution) #TODO might need a english screen too
# level screens
level_files = []
for f in os.listdir(screens_folder):
	if "level_" in f.lower() and f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
		#print(f)
		level_files.append(os.path.join(screens_folder, f))

level_screens = []
for o in level_files:
	level_screens.append(cv2.resize(cv2.cvtColor(cv2.imread(o), cv2.COLOR_BGR2GRAY), downscale_resolution))
# prepare OHMSS screens 
ohmss_files = []
for f in os.listdir(screens_folder):
	if "ohmss" in f.lower() and f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
		#print(f)
		ohmss_files.append(os.path.join(screens_folder, f))

ohmss_screens = []
for o in ohmss_files:
	ohmss_screens.append(cv2.resize(cv2.cvtColor(cv2.imread(o), cv2.COLOR_BGR2GRAY), downscale_resolution))
print("Prepared")

last_maxes = []
last_statuses = ["Started. Select level!"]
last_message = ""
loaded_total_time = 0.0
attempts_session = 0
attempts_total = 0
time_session = 0.0
total_time = 0.0
time_started = 0.0
time_before_paused = 0
Paused = False
current_level = "No Level"
display_title = "Select Level"
level_started = False
time_at_same_screen = False
timer_color = color_inactive
attempt_color = color_regular

loop_start = time.time()
loop_fps = 0
fps_counter = 0

print("Starting loop")
while True: # Main loop
	status_view = numpy.zeros((400,300,3), numpy.uint8)

	if Paused:
		cv2.putText(status_view, "Paused", (10,70), font, fontScale, (0,255,255), thickness, cv2.LINE_AA)
		cv2.putText(status_view, "press P to unpause", (10,100), font, 0.7, (255,255,255), 1, cv2.LINE_AA)
	else:
		game_capture = screenshotRegion(pfTop, pfLeft, pfWidth, pfHeight)
		game_comp = cv2.resize( cv2.cvtColor(game_capture, cv2.COLOR_BGR2GRAY ), downscale_resolution )
		#cv2.imshow("game_comp", game_comp) # show capture region

		most_likely = [0, "?"]

		if current_level == "No Level": 
			# only look for a new level if we have no level
			display_title = "Select Level"
			target_fps = 10

			i = 0
			for o in level_screens:
				d = compare_l2_norm(game_comp, o)
				if d > most_likely[0]:
					name = level_files[i]
					most_likely = [d, name]
					#cv2.imshow("most matching level", o)
				i += 1
				
			diffcomp = compare_l2_norm(game_comp, difficulty_frame) # difficulty screen looks annoyingingly similar to Cradle
			#print(diffcomp)
			# we seem to be at a level description = Level selected!
			if "level_" in most_likely[1].lower() and current_level == "No Level" and diffcomp < most_likely[0] and most_likely[0] > level_match_threshold:
				#last_statuses.append("Level selected")
				string = os.path.basename(most_likely[1]) # get level name/diff from img filename
				level_name = string.split("_")[1]
				difficulty_name = string.split("_")[2]
				current_level = level_name + " " + difficulty_name
				last_statuses.append(current_level + " selected (" + (percentage(most_likely[0])) + ")")

				print("Level Match:", current_level, percentage(most_likely[0]))

				display_title = current_level
				level_started = False

				# load data
				loaded_data = load_data(current_level)
				attempts_total = loaded_data["attempts"]
				loaded_total_time = loaded_data["time"]

		elif current_level != "No Level":
			target_fps = 20
			# a level is selected, dont compare every levels description then

			# compare against black
			black_comp = compare_l2_norm(game_comp, black_frame)

			# compare level select screens
			level_select_comp_jp = compare_l2_norm(game_comp, level_select_frame_jp)
			level_select_comp_en = compare_l2_norm(game_comp, level_select_frame_en)
			if level_select_comp_en > level_select_comp_jp:
				level_select_comp = level_select_comp_en
			else:
				level_select_comp = level_select_comp_jp

			# compare OHMSS screens, these flash through after an attempt
			i = 0
			for o in ohmss_screens:
				d = compare_l2_norm(game_comp, o)
				if d > most_likely[0]:
					most_likely = [d, "OHMSS"]
				i += 1

			# now lets see where we are:

			# we are at the level select
			if level_select_comp > 0.9 and level_select_comp > most_likely[0]:
				if not time_at_same_screen and level_started:
					time_at_same_screen = time.time()
				else:
					duration = time.time() - time_at_same_screen
					if duration > level_select_screen_wait or not level_started: # we have been here for enough time, consider it a level change
						most_likely = [level_select_comp, "Level Select Screen"]
						if level_started:
							# maybe subtract time_at_same_screen here since you wait n seconds to end the session but idk if anyone rly cares
							save_data(current_level, attempts_total, total_time)
							last_statuses.append("Saved " + current_level)
						attempts_session = 0
						attempts_total = 0
						loaded_total_time = 0.0
						total_time = 0.0
						time_session = 0.0
						current_level = "No Level"
						display_title = "Select Level"
						level_started = False
						time_at_same_screen = False
						timer_color = color_inactive
					elif level_started: # we're just flashing through here quickly, not a level change
						s = "Ending session in " + str(round(level_select_screen_wait - duration))
						cv2.putText(status_view, s, (10, 300), font, 0.5, color_paused, 1, cv2.LINE_AA)

			# we are at black (between ohmss menu and in-game, ... and also the camera in bunker1)
			elif black_comp > 0.97 and black_comp > most_likely[0]:
				most_likely = [black_comp, "Black"]	

			# no good match on anything, probably in-game then
			elif most_likely[0] < 0.8: 
				most_likely[1] = "In-game"

			else:
				#print("else reached")
				time_at_same_screen = False

			# status logic
			current_status = most_likely[1]
			last_status = last_statuses[-1]
			if current_status != last_status:
				print(percentage(most_likely[0]), ": Went from", last_status, "to", current_status)
				last_statuses.append(current_status)

				if len(last_statuses) > 10: # we dont need to keep many statuses
					del last_statuses[0]

			# attempt logic
			if len(last_statuses) > 3 and current_level != "No Level":
				attempt_sequence = False
				#if last_statuses[-3] == "OHMSS" and last_statuses[-2] == "Black" and last_statuses[-1] == "In-game" and level_started: # original, triggers on new attempt cinema, seems reliable
				if last_statuses[-4] == "In-game" and last_statuses[-3] == "Black" and last_statuses[-2] == "OHMSS" and last_statuses[-1] == "Black" and level_started: # new, triggers on black after ohmss
					# this is triggered between attempts
					attempt_sequence = True
				elif last_statuses[-2] == "OHMSS" and last_statuses[-1] == "Black" and not level_started:
					# this is the first attempt (will also match if you reset your console after selecting level)
					print("Good luck")
					attempt_sequence = True
					time_started = time.time()
					level_started = True

				if attempt_sequence:
					last_statuses.append("Attempt")
					print("Attempt")
					attempt_color = color_flash # this will flash the attempt counter font
					attempts_total += 1
					attempts_session += 1

					# auto save every n session tries
					if attempts_session % auto_save_frequency == 0:
						print("Auto-Saving")
						last_statuses.append("Auto-Saved " + current_level)
						save_data(current_level, attempts_total, total_time)

				else:
					attempt_color = color_regular # white

		# title
		cv2.putText(status_view, display_title, (10,30), font, fontScale, (255,255,255), thickness, cv2.LINE_AA)
		# highest match
		#cv2.putText(status_view, most_likely[1] + " = " + percentage(most_likely[0]), (10, 370), font, 0.5, (255,255,255), 1, cv2.LINE_AA)

		# history
		if len(last_statuses) > 3: # TODO show this immediately instead of waiting for 3 statuses
			cv2.putText(status_view, last_statuses[-3], (10,330), font, 0.4, (105,105,105), 1, cv2.LINE_AA)
			cv2.putText(status_view, last_statuses[-2], (10,345), font, 0.4, (150,150,150), 1, cv2.LINE_AA)
			cv2.putText(status_view, ">" + last_statuses[-1], (10,360), font, 0.4, (220,220,220), 1, cv2.LINE_AA)

		# draw stats if we are playing
		if current_level != "No Level":
			if level_started:
				if time_at_same_screen:
					timer_color = color_paused
					time_session = (time.time() - time_started) + time_before_paused - (time.time() - time_at_same_screen)
				else:
					timer_color = color_running
					time_session = (time.time() - time_started) + time_before_paused
				#cv2.putText(status_view, display_time(time_session, decimals_shown), (10,150), font, 0.8, timer_color, 1, cv2.LINE_AA)
			else: # before first attempt
				time_session = 0
				attempt_color = color_inactive
				timer_color = color_inactive
				s = "Waiting for attempt..."
				cv2.putText(status_view, s, (10, 300), font, 0.5, color_regular, 1, cv2.LINE_AA)

			total_time = time_session + loaded_total_time

			cv2.putText(status_view, "Session", (10,90), font, 1, (0,255,255), thickness, cv2.LINE_AA)
			cv2.putText(status_view, "Attempts: " + str(attempts_session), (10,120), font, 0.8, attempt_color, 1, cv2.LINE_AA)
			cv2.putText(status_view, display_time(time_session), (10,150), font, 0.8, timer_color, 1, cv2.LINE_AA)

			cv2.putText(status_view, "Total", (10,200), font, 1, (0,128,255), thickness, cv2.LINE_AA)
			cv2.putText(status_view, "Attempts: " + str(attempts_total), (10,230), font, 0.8, attempt_color, 1, cv2.LINE_AA)
			cv2.putText(status_view, display_time(total_time), (10,260), font, 0.8, timer_color, 1, cv2.LINE_AA)

	
	### input handling
	k = cv2.waitKey( int(wait_delay) ) # requires int
	if k == ord("q"): # press q to quit
		#save_data(current_level, attempts_total) # save on quit
		print("Bye")
		cv2.destroyAllWindows()
		sys.exit(0)
		break
	elif k == ord("r"): # press r to reset attempts
		print("Reset (S)ession or (T)otal?")
		choice = False
		cv2.waitKey(wait_delay) # TODO this is wonky as hell, make it better
		while not choice:
			choice = input("S or T: ")
			if choice.lower() == "s":
				print("Reset session")
				attempts_session = 0
				time_session = 0.0
			elif choice.lower() == "t":
				print("Reset total")
				attempts_total = 0
				total_time = 0.0
	elif k == ord("s"):
		if current_level != "No Level":
			save_data(current_level, attempts_total, total_time)
		else:
			print("Cannot save: no level selected")
	elif k == ord("-"):
		level_match_threshold -= 0.005
		print("New threshold:", level_match_threshold)
		current_level = "No Level"
	elif k == ord("+"):
		level_match_threshold += 0.005
		print("New threshold:", level_match_threshold)
		current_level = "No Level"
	# elif k == ord("p"): #TODO Fix, this used to work but broke at some point after adding the level select delay
	# 	if not Paused:
	# 		if level_started:
	# 			time_before_paused = time_session
	# 		Paused = True
	# 		print("Paused")
	# 	elif Paused:
	# 		if level_started:
	# 			time_started = time.time()
	# 		Paused = False
	# 		print("Unpaused")
	# TODO add button (maybe G?) for changing screen region

	cv2.putText(status_view, "" + percentage(most_likely[0]) + "/" + percentage(level_match_threshold), (210,385), font, 0.4, (255,255,255), 1, cv2.LINE_AA)
	cv2.putText(status_view, "" + str(loop_fps) + "/" + str(target_fps) + " (" + str(wait_delay) + ")", (10,385), font, 0.4, (255,255,255), 1, cv2.LINE_AA)
	cv2.imshow("Boris", status_view)

	fps_counter += 1
	if (time.time() - loop_start) > 0.3: 
		loop_fps = int( fps_counter/(time.time() - loop_start) )
		fps_counter = 0
		loop_start = time.time()

		if loop_fps > target_fps:
			wait_delay += 1 #TODO adjust faster by having dynamic increments
		elif loop_fps < target_fps:
			wait_delay -= 1
			if wait_delay < 1:
				wait_delay = 1
		# else fps == target_fps, the wait_delay is preem