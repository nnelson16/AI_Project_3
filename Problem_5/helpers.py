import sys
import time
import random
import os
from copy import deepcopy, copy
from shutil import rmtree
from math import log10,log1p

import numpy as np

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib import cm
from matplotlib import mlab as ml
from matplotlib import colors

import imageio
import threading

map_name = ""
traversal_name = ""
save_base = "" 
png_managers = []
started_png_managers = 0

# writes a gif in parent_folder made up of all it's sorted .png files
def make_gif(parent_folder):
	items = os.listdir(parent_folder)
	png_filenames = []
	for elem in items:
		if elem.find(".png")!=-1 and elem.find("heatmap")!=-1:
			png_filenames.append(elem)

	sorted_png = []
	while True:
		lowest = 10000000
		lowest_idx = -1
		for p in png_filenames:
			val = int(p.split("-")[2].split(".")[0])
			if lowest_idx==-1 or val<lowest:
				lowest = val
				lowest_idx = png_filenames.index(p)
		sorted_png.append(png_filenames[lowest_idx])
		del png_filenames[lowest_idx]
		if len(png_filenames)==0: break
	png_filenames = sorted_png

	with imageio.get_writer(parent_folder+"/prediction-heatmap.gif", mode='I',duration=0.2) as writer:
		for filename in png_filenames:
			image = imageio.imread(parent_folder+"/"+filename)
			writer.append_data(image)

def create_png(src_tsv,targ_png,trav_so_far,dpi):
	#print(src_tsv+" "+targ_png+" ",trav_so_far)
	actual_location = trav_so_far[-1]
	zs = []
	smallest_z = 10

	f = open(src_tsv,"r")
	rows = f.read().split("\n")
	for y in range(len(rows)):
		row = []
		src_row = rows[y].split("\t")
		if len(src_row) in [0,1]: continue
		for item in src_row:
			val = float(item)
			row.append(val)
			if val<smallest_z and val!=0: smallest_z = val
		zs.append(row)

	smallest_scaled_z = 10
	for y in range(len(zs)):
		row = []
		for x in range(len(zs[y])):
			if zs[y][x]==0.0: val = smallest_z-(smallest_z/2.0)
			else: val = zs[y][x]
			zs[y][x] = val
			if val<smallest_scaled_z: smallest_scaled_z = val

	Z = np.array(zs)

	fig,ax = plt.subplots()

	png_title = targ_png.split("/")[1]+" | "+targ_png.split("/")[2]+" | "
	png_title += src_tsv.split("/")[-1].split(".")[0].split("-")[-1]

	fig.suptitle(png_title,fontsize=12,y=1.02)

	ax.set_xlabel("X Coordinate")
	ax.set_ylabel("Y Coordinate")

	ax.xaxis.set_label_position('top')
	ax.xaxis.tick_top()

	text_x = 1
	#text_y = int(len(zs)/10)
	text_y = 5

	ax.annotate('Actual Agent Location',xy=(actual_location[0],actual_location[1]),xytext=(text_x,text_y),
				arrowprops=dict(arrowstyle="-"), color='white') #ha="right",va="center")   #facecolor='white',shrink=0.01), color='white')

	#cax = ax.imshow(Z,cmap='plasma',norm=colors.LogNorm(vmin=smallest_scaled_z, vmax=1.0))
	cax = ax.imshow(Z,cmap='plasma')
	#cax = ax.imshow(Z,cmap='plasma',norm=colors.LogNorm(vmin=Z.min(),vmax=Z.max()))

	#trav_xs = []
	#trav_ys = []
	#for s in trav_so_far:
	#	trav_xs.append(s[0])
	#	trav_ys.append(s[1])
	#ax.plot(trav_xs,trav_ys,lw=0.1,c='white')

	ticks = [smallest_scaled_z,Z.max()]
	ylabels = ["%0.5f"%smallest_scaled_z,"%0.5f"%Z.max()]

	cbar = fig.colorbar(cax,ticks=ticks)
	cbar.ax.set_yticklabels(ylabels)

	#save_spot = save_base+"prediction-heatmap-"+str(iteration)+".png"
	fig.savefig(targ_png,bbox_inches='tight',dpi=dpi)
	plt.close()

# runs in separate thread, handles writing the png files
def png_manager(scaled_zs,iteration,actual_location,smallest_scaled_z,traversal_name):
	global started_png_managers
	started_png_managers+=1

	sys.stdout.write("\rpng_manager ("+str(map_name)+" - "+str(traversal_name)+" - "+str(iteration)+") online.                                                                \n")
	sys.stdout.flush()

	Z = np.array(scaled_zs)

	fig,ax = plt.subplots()
	fig.suptitle(map_name+" - "+traversal_name+" - ("+str(iteration)+")",fontsize=12,y=1.02)

	ax.set_xlabel("X Coordinate")
	ax.set_ylabel("Y Coordinate")

	ax.xaxis.set_label_position('top')
	ax.xaxis.tick_top()

	ax.annotate('Actual Location',xy=(actual_location[0],actual_location[1]+1),xytext=(1,1),
				arrowprops=dict(facecolor='white',shrink=0.05), color='white')

	cax = ax.imshow(Z,cmap='plasma',norm=colors.LogNorm(vmin=smallest_scaled_z, vmax=1.0))
	#cax = ax.imshow(Z,cmap='plasma')
	cbar = fig.colorbar(cax, ticks=[smallest_scaled_z,Z.max()])
	cbar.ax.set_yticklabels(['0.0',str(Z.max())[:7]])

	save_spot = save_base+"prediction-heatmap-"+str(iteration)+".png"
	fig.savefig(save_spot,bbox_inches='tight',dpi=200)
	plt.close()

	started_png_managers-=1

execution_done = False

def thread_starter():
	global started_png_managers
	global png_managers

	started_png_managers = 0
	#while True:
	#	if execution_done: return
	for a in png_managers:
		a.start()
		#time.sleep(1.0)

	while started_png_managers>0:
		time.sleep(0.1)

# get the bounding box of the input sequence
def get_sequence_bounds(sequence):
	y_max, x_max, x_min, y_min = None, None, None, None
	for x,y in sequence:
		if x_max==None: x_max = x
		if x_min==None: x_min = x
		if y_max==None: y_max = y
		if y_min==None: y_min = y

		if x<x_min: x_min = x
		if x>x_max: x_max = x
		if y<y_min: y_min = y
		if y>y_max: y_max = y
	return x_max,y_max,x_min,y_min

class viterbi_node:
	def __init__(self):
		self.value = ""
		self.parent = None

		self.best_path = None
		self.best_path_cost = None

		self.parents 	  = []
		self.parent_costs = []

class viterbi_matrix:
	def __init__(self,num_rows=3,num_cols=3,values=["H","H","T","N","N","N","N","B","H"],load_path=None):
		global png_managers
		global started_png_managers
		global execution_done

		png_managers = []
		started_png_managers = 0
		execution_done = False

		self.started_thread_manager = False
		self.thread_manager = threading.Thread(target=thread_starter)
		#self.thread_manager.start()

		self.temp_anc_matrix = None # debugging
		self.display_temp_ancestor_matrix = False

		# Questions A & B...
		if load_path is None:
			self.actual_traversal_path = None
			self.num_rows = num_rows
			self.num_cols = num_cols
			self.values = values
			self.init_conditions_matrix(values)
			self.init_prediction_matrix()

		# Question D...
		else:
			self.load_path = load_path
			self.load_conditions_matrix()

	def start_png_managers(self):
		self.thread_manager.start()

	def signal_exit(self):
		global execution_done
		execution_done = True

	# loads a grid world matrix from a .tsv file
	def load_conditions_matrix(self,print_all=True):
		# ensure the .tsv file exists
		if not os.path.exists(self.load_path):
			print("\nWARNING: Could not find .tsv file "+self.load_path+"\n")
			return

		if print_all: sys.stdout.write("\nLoading \""+self.load_path+"\"... ")
		f = open(self.load_path,"r")
		text = f.read()
		lines = text.split("\n")

		self.conditions_matrix = []
		self.num_cols = None

		for line in lines:
			elems = line.split("\t")
			if len(elems)<2: break # break if line doesn't make sense to exist
			row = []
			for elem in elems:
				new_node = viterbi_node()
				new_node.value = elem
				row.append(new_node)
			if self.num_cols is None: self.num_cols = len(row)
			else:
				if len(row) != self.num_cols:
					if print_all: sys.stdout.write("warning, ")
					row = row[:self.num_cols]
			self.conditions_matrix.append(row)
		self.num_rows = len(self.conditions_matrix)
		if print_all: sys.stdout.write("success. ")
		if print_all: sys.stdout.write("Rows: "+str(self.num_rows)+", Columns: "+str(self.num_cols)+"\n")
		f.close()

	# reloads the prior conditions_matrix from same file (resets current weights)
	def reload_conditions_matrix(self):
		self.load_conditions_matrix(print_all=False)

	# sets up directory for saving plot png's to
	def init_plot_directory(self,save_dir):
		#global map_name
		#global traversal_name
		#global save_base

		# check to ensure directory structure exists
		path_items = save_dir.split("/")
		self.map_name = path_items[1]
		self.traversal_name = path_items[2]

		#map_name = path_items[1]
		#traversal_name = path_items[2]

		if not os.path.exists(path_items[0]):
			os.makedirs(path_items[0])
		else:
			if not os.path.exists(path_items[0]+"/"+path_items[1]):
				os.makedirs(path_items[0]+"/"+path_items[1])
			else:
				if os.path.exists(path_items[0]+"/"+path_items[1]+"/"+path_items[2]):
					rmtree(path_items[0]+"/"+path_items[1]+"/"+path_items[2])
		os.makedirs(path_items[0]+"/"+path_items[1]+"/"+path_items[2])
		self.save_base = save_dir+"/"

	# loads in observations
	def load_observations(self,observation_path,grid_width=-1,grid_height=-1,path=False,method="default",save_dir=None,print_nothing=True):

		# set up directory to save data to
		if save_dir is not None: self.init_plot_directory(save_dir) # if saving plot pictures
		else: self.save_base = None

		# ensure the file exists
		if not os.path.exists(observation_path):
			print("\nWARNING: Could not find "+observation_path+"\n")
			return

		sys.stdout.write("\nLoading \""+observation_path+"\"... ")
		f = open(observation_path,"r")
		text = f.read()
		lines = text.split("\n")

		self.actual_traversal_path = [] # loaded from provided file

		self.observed_actions  = [] # to be filled as we encounter more actions
		self.observed_readings = [] # to be filled as we encounter more readings

		self.queued_actions  = [] # filled with all initial actions (loaded from file)
		self.queued_readings = [] # filled with all initial readings (loaded from file)

		self.start_location 	= None
		self.print_prediction   = True
		current_item_type   	= None

		for line in lines:
			if line.find("start_location")!=-1:
				x,y = line.split(" - ")[1].split(",")
				self.start_location = [int(x.replace("(","")),int(y.replace(")",""))]

			elif line.find("~")!=-1:
				if current_item_type==None: current_item_type = "actual_traversal_path"
				elif current_item_type=="actual_traversal_path": current_item_type = "queued_actions"
				elif current_item_type=="queued_actions": current_item_type = "queued_readings"
				else: break
			else:
				if current_item_type=="actual_traversal_path":
					x,y = line.split(",")
					self.actual_traversal_path.append([int(x.replace("(","")),int(y.replace(")",""))])
				else: self.__dict__[current_item_type].append(line)

		if len(self.queued_actions)!=len(self.queued_readings):
			sys.stdout.write("failure: observations invalid\n")
			return

		sys.stdout.write("success. ")
		print("Path: "+str(len(self.actual_traversal_path))+", Observations: "+str(len(self.queued_readings)))

		#self.transition_matrices = []

		# trim the environment down to a smaller area containing the real movement of the agent
		if grid_width!=-1 and grid_height!=-1: self.adjust_environment_bounds(grid_width,grid_height)

		# initialize the self.prediction_matrices list
		self.init_prediction_matrix()

		self.print_transition       = False
		self.print_condition  	    = True
		self.print_actual_traversal = True
		self.print_ancestors 		= False

		self.move_index = 1
		self.current_predicted_length = 1

		print_size = 6
		if not print_nothing:
			self.print_current_state(print_size)
		else:
			sys.stdout.write("Executing... ")
			sys.stdout.flush()

		max_limit = len(self.queued_readings)
		#max_limit = 10

		# if we are performing path approximations, print the full actual path on each iteration
		self.print_full_traversal = False if path else True

		# open files used for logging data
		if save_dir is not None: log_file = open(self.save_base+"meta.txt","w")
		if save_dir is not None: anc_file = open(self.save_base+"anc.txt","w")

		start_time = time.time()
		total_score = 0
		i=0

		for self.cur_action,self.cur_reading in zip(self.queued_actions[:max_limit],self.queued_readings[:max_limit]):

			# add the observation
			self.add_observation()

			# update weights given the new information
			self.update_weights()

			# print out current state information
			if not print_nothing: self.print_current_state(print_size)

			# if calculating the most likely sequences as well...
			if path:
				# get the current sequence
				pred_seq,pred_prob,score = self.get_predicted_sequence(score=True)
				total_score+=score

				self.current_predicted_length = len(pred_seq)

				if not print_nothing:
					# print out current sequence
					sys.stdout.write("\n Current PREDICTED Agent Traversal (Probability = ")
					sys.stdout.write("%0.5f" % pred_prob[-1])
					sys.stdout.write(", Score = "+str(score)+")...\n")
					self.print_single_sequence(pred_seq)
				else:
					sys.stdout.write("\rExecuting... "+"("+str(i+1)+"/"+str(max_limit)+") score: "+str(score)+", total: "+str(total_score)+" ")
					sys.stdout.flush()

				if save_dir is not None:
					self.save_predicted_sequence(pred_seq,pred_prob,i+1,"traversal_sequence")

				if (i+1) in [10,50,100]:
					trajectories,probabilities = self.get_predicted_sequences()
					self.save_predicted_sequences(i+1,trajectories,probabilities)

			if save_dir is not None:
				# save ancestor data for current prediction matrix
				if self.print_ancestors: self.save_anc_info(i+1,anc_file)
				# save the current prediction matrix
				self.save_prediction_matrix(i+1)

				log_file.write("Iteration #"+str(i+1)+"\n")
				log_file.write("Action: "+str(self.cur_action)+", Reading: "+str(self.cur_reading)+"\n")

				if path:
					log_file.write("Predicted Path Probability: ")
					log_file.write("%0.5f" % pred_prob[-1])
					log_file.write("\n")
					log_file.write("Predicted Path Length: "+str(len(pred_seq))+"\n")
					log_file.write("Predicted Path Score: "+str(score)+", Total Score: "+str(total_score)+"\n")

					p_x,p_y = pred_seq[-1]
					a_x,a_y = self.actual_traversal_path[len(pred_seq)-1]

					log_file.write("Predicted Current Location: ("+str(p_x)+","+str(p_y)+")\n")
					log_file.write("Actual Current Location: ("+str(a_x)+","+str(a_y)+")\n")
					log_file.write("Value at Actual: "+self.conditions_matrix[a_y][a_x].value+"\n")

				log_file.write("...\n")

			i+=1

		if not print_nothing:
			final_loc = self.actual_traversal_path[-1]
			print("\nActual Final Location: ("+str(final_loc[0])+", "+str(final_loc[1])+")")
			print("Actual traversal path length: "+str(len(self.actual_traversal_path)))

			if path:
				pred_final_loc = pred_seq[-1]
				print("\nPredicted Final Location: ("+str(pred_final_loc[0])+", "+str(pred_final_loc[1])+")")
				print("Predicted traversal path length: "+str(len(pred_seq)))
			print("\n")
		else:
			sys.stdout.write("- Done -  Total time: "+str(time.time()-start_time)+"\n\n")

		if save_dir is not None:
			final_loc = self.actual_traversal_path[-1]
			self.save_actual_sequence()
			log_file.write("\n\nActual Final Location ("+str(final_loc[0])+", "+str(final_loc[1])+")\n")
			log_file.write("Actual traversal path length: "+str(len(self.actual_traversal_path))+"\n")

			if path:
				pred_final_loc = pred_seq[-1]
				log_file.write("Predicted Final Location: ("+str(pred_final_loc[0])+", "+str(pred_final_loc[1])+")\n")
				log_file.write("Predicted traversal path length: "+str(len(pred_seq))+"\n")

			log_file.write("Total Time: "+str(time.time()-start_time)+"\n")
			log_file.close()

		if path:
			return total_score

	# saves a list of predicted sequences to the same file
	def save_predicted_sequences(self,iteration,trajectories,probs):
		filename = self.save_base+"prediction-likely_trajectories-"+str(iteration)+".txt"
		f = open(filename,"w")

		for t,p in zip(trajectories,probs):
			f.write("\n~~~\n")
			f.write("\nSequence Probability: "+str(p)+"\n")
			self._write_single_sequence(t,device=f)
		f.close()

	# get the num_loc most likely locations in the current predictions matrix
	def predict_locations(self,num_loc):
		mat = self.prediction_matrices[-1]
		pred_locs = [] # predicted locations
		loc_probs = [] # predicted probabilities
		# get the num_loc most likely ending locations
		while len(pred_locs)<num_loc:
			cur_loc,cur_prob = self.predict_location(mat,exclude=pred_locs)
			pred_locs.append(cur_loc)
			loc_probs.append(cur_prob)
		return pred_locs,loc_probs

	# gets the num_seq most likely traversal sequences given the current state
	def get_predicted_sequences(self,num_seq=10,score=True):
		# get num_seq most likely ending locations on the current prediction matrix
		seq_end_locs,seq_probs = self.predict_locations(num_seq)
		pred_seqs = []
		# iterate over returned end locations and reconstruct path
		for loc in seq_end_locs:
			pred_seqs.append(self.rectify_path(loc))
		return pred_seqs,seq_probs

	# takes an ending location (x,y) and follows it back (starting with the most recent prediction matrix) until
	# it finds a cell with no parents, i.e. the starting location
	def rectify_path(self,end_location):
		path = [end_location]
		cur_x, cur_y = end_location[0],end_location[1]
		cur_cell = self.prediction_matrices[-1][cur_y][cur_x]
		while True:
			cur_parent = cur_cell.parent
			if cur_parent==None: return path
			path.insert(0,cur_parent.coords)
			cur_cell = cur_parent
		return path

	# writes a predicted traversal sequence out to file
	def save_predicted_sequence(self,preq_seq,pred_prob,iteration,name):
		save_spot = self.save_base+"prediction-"+name+"-"+str(iteration)+".txt"
		f = open(save_spot,"w")
		self._write_single_sequence(preq_seq,device=f)
		f.close()

	# writes the actual traversal path out to a file 
	def save_actual_sequence(self):
		save_spot = self.save_base+"actual_traversal_sequence.txt"
		f = open(save_spot,"w")
		self._write_single_sequence(self.actual_traversal_path,device=f)
		f.close()

	# saves the current prediction matrix in .tsv format
	def save_prediction_matrix(self,iteration):
		cur_pred_matrix = self.prediction_matrices[-1]
		save_spot = self.save_base+"prediction-floats-"+str(iteration)+".tsv"

		f = open(save_spot,"w")
		for y in range(self.num_rows):
			for x in range(self.num_cols):
				elem = cur_pred_matrix[y][x].value
				f.write(str(elem))
				if x != self.num_cols-1: f.write("\t")
				else: f.write("\n")
		f.close()

	# save a png of the current prediction matrix in heat map form
	def save_heatmap(self,iteration):

		cur_pred_matrix = self.prediction_matrices[-1]
		actual_location = self.actual_traversal_path[self.current_predicted_length-1]

		zs = []
		smallest_z = 10

		for y in range(self.num_rows):
			row = []
			for x in range(self.num_cols):
				row.append(float(cur_pred_matrix[y][x].value))
				if cur_pred_matrix[y][x].value<smallest_z and cur_pred_matrix[y][x].value!=0:
					smallest_z = cur_pred_matrix[y][x].value
			zs.append(row)

		scaled_zs = []
		smallest_scaled_z = 100
		for y in range(self.num_rows):
			row = []
			for x in range(self.num_cols):
				if zs[y][x]==0.0:
					val = smallest_z-(smallest_z/2.0)
				else:
					val = zs[y][x]
				logged_val = val
				if logged_val<smallest_scaled_z: smallest_scaled_z = logged_val
				row.append(logged_val)
			scaled_zs.append(row)
		#Z = np.array(scaled_zs)

		png_creator = threading.Thread(target=png_manager,args=(copy(scaled_zs),copy(iteration),copy(actual_location),copy(smallest_scaled_z),copy(self.traversal_name)))
		png_managers.append(png_creator)

	# various methods for ensuring data validity
	def check_validity(self):
		# check that all prediction_matrices are of the same size as the conditions_matrix
		for m in self.prediction_matrices:
			if len(m)!=len(self.conditions_matrix): print("WARNING: Invalid y bounds")
			for row_idx in range(len(m)):
				if len(m[row_idx])!=len(self.conditions_matrix[row_idx]): print("WARNING: Invalid x bounds")

	# given that the actual path taken by the agent rarely fills anywhere near the entire conditions_matrix
	# we can choose to trim the conditions_matrix down to fit the range of the path taken
	def adjust_environment_bounds(self,grid_width,grid_height):

		# get the bounding region for the actual traversal path in the grid world
		x_max,y_max,x_min,y_min = get_sequence_bounds(self.actual_traversal_path)

		# get the current path span
		x_span = x_max-x_min
		y_span = y_max-y_min

		if x_span>grid_width:
			print("WARNING: Path wider than specified grid_width ("+str(grid_width)+")")
			return

		if y_span>grid_height:
			print("WARNING: Path taller than specified grid_height ("+str(grid_height)+")")
			return

		# calculate approx. buffer region widths
		x_buf = int((grid_width-x_span)/2)
		y_buf = int((grid_height-y_span)/2)

		# add buffer regions to real bounds
		x_max += x_buf
		x_min -= x_buf
		y_max += y_buf
		y_min -= y_buf

		# calculate new spans after buffers are added
		new_x_span = x_max-x_min+1
		new_y_span = y_max-y_min+1

		# correct rounding errors on the /2 division
		while new_x_span!=grid_width:
			if new_x_span<grid_width: x_max+=1
			if new_x_span>grid_width: x_max-=1
			new_x_span = x_max-x_min+1
		while new_y_span!=grid_height:
			if new_y_span<grid_height: y_max+=1
			if new_y_span>grid_height: y_max-=1
			new_y_span = y_max-y_min+1

		# translate the start_location coordinate
		self.start_location = [self.start_location[0]-x_min,self.start_location[1]-y_min]

		# translate the actual traversal path to fit new region
		self.translate_actual_path(-1*x_min,-1*y_min)

		# trim down the size of the conditions matrix to fit new region
		self.trim_conditions_matrix(x_max,y_max,x_min,y_min)

		# set values for number of rows and columns
		self.num_rows, self.num_cols = grid_height, grid_width

		#print("\nLength of conditions matrix = "+str(len(self.conditions_matrix)))
		#print("Width of conditions matrix = "+str(len(self.conditions_matrix[0])))

	# translates the coordinates of the actual traversal path
	def translate_actual_path(self,x_offset,y_offset):
		for i in range(len(self.actual_traversal_path)):
			self.actual_traversal_path[i] = [self.actual_traversal_path[i][0]+x_offset,self.actual_traversal_path[i][1]+y_offset]

	# trims the conditions matrix so it fits in specified bounds
	def trim_conditions_matrix(self,x_max,y_max,x_min,y_min):
		self.conditions_matrix = self.conditions_matrix[y_min:y_max+1]
		for i in range(len(self.conditions_matrix)):
			self.conditions_matrix[i] = self.conditions_matrix[i][x_min:x_max+1]

	# returns the number of blocked cells in the self.conditions_matrix
	def get_num_blocked_cells(self):
		num_blocked = 0
		for y in range(self.num_rows):
			for x in range(self.num_cols):
				if self.conditions_matrix[y][x].value=="B": num_blocked+=1
		return num_blocked

	# creates a new condition matrix given the provided conditions
	def init_conditions_matrix(self,conditions=None):
		if conditions is not None: self.values = conditions
		self.conditions_matrix = []
		for y in range(self.num_rows):
			row = []
			for x in range(self.num_cols):
				new_node = viterbi_node()
				new_node.value = self.values[y*self.num_cols+x]
				row.append(new_node)
			self.conditions_matrix.append(row)

	# clears the current prediction_matrices list and creates a new prediction matrix
	# to be inserted at the first location in the list, all initial probabilities are set to 1/8
	# besides the location containing "B" which has it's probability set to 0
	def init_prediction_matrix(self,start_location=None):
		if start_location==None:
			init_probability = 1.0/float(self.num_rows*self.num_cols-self.get_num_blocked_cells())
			self.init_probability = init_probability
			self.prediction_matrices = []
			cells = []
			for y in range(self.num_rows):
				row = []
				for x in range(self.num_cols):
					new_node = viterbi_node()
					new_node.parent = None
					new_node.coords = [x,y]
					new_node.value = init_probability if self.conditions_matrix[y][x].value!="B" else 0.0
					#if self.conditions_matrix[y][x].value=="B": new_node.value = 0.0
					row.append(new_node)
				cells.append(row)
			self.prediction_matrices.append(cells)
		else:
			self.prediction_matrices = []
			cells = []
			for y in range(self.num_rows):
				row = []
				for x in range(self.num_cols):
					new_node = viterbi_node()
					new_node.parent = None
					new_node.coords = [x,y]
					new_node.value = 1.0 if x==start_location[0] and y==start_location[1] else 0.0
					row.append(new_node)
				cells.append(row)
			self.prediction_matrices.append(cells)

	# add a single observed action and observed reading while also incrementing the move index
	def add_observation(self):
		self.observed_actions.append(self.cur_action)
		self.observed_readings.append(self.cur_reading)
		self.move_index+=1

	# creates a new prediction matrix given the provided conditions
	def empty_prediction_matrix(self):
		cells = []
		for y in range(self.num_rows):
			row = []
			for x in range(self.num_cols):
				new_node = viterbi_node()
				new_node.value = 0.0
				new_node.parent = None
				new_node.coords = [x,y]
				row.append(new_node)
			cells.append(row)
		return cells

	# cur_action: reported movement direction in this step
	# cur_reading: reported reading in this step
	# condition_matrix: condition matrix (strings)
	# pred_matrix: current prediction matrix (floats)
	#
	# return: updated prediction matrix (given a new move)
	def update_weights(self):

		# if we have already updated the weights for the most recent observation
		if len(self.observed_actions)+1==len(self.prediction_matrices):
			print("ERROR: update_weights()")
			return

		# set local variables to hold the last observed action and observed reading
		cur_action 	= self.cur_action
		cur_reading = self.cur_reading

		old_pred_matrix 	= self.prediction_matrices[-1] # get the last prediction matrix
		transition_matrix 	= self.empty_prediction_matrix() # create new matrix
		condition_matrix 	= self.conditions_matrix # matrix holding cell conditions

		# iterate over all x,y in matrix and set values for new transition matrix
		for y in range(self.num_rows):
			for x in range(self.num_cols):
				if condition_matrix[y][x].value=="B":
					transition_matrix[y][x].value==0.0
				else:
					# to be filled with pointers to all possible parents
					transition_matrix[y][x].parents = []

					# to be filled with the transition costs of all possible parents
					transition_matrix[y][x].parent_costs = []

					# get all possible neighbors
					ns = self.get_neighbors([x,y])

					# value of this cell from last iteration
					myself_anc_prob = old_pred_matrix[y][x].value
					myself_prob_given_anc = 0.0

					highest_anc_prob = 0.0
					total_anc_prob = 0.0

					# get the probabilities of having descended from any of the possible neighbors
					for n_x,n_y in ns:
						if n_x==x and n_y==y: continue # if the current cell, skip (handle after loop)
						if condition_matrix[n_y][n_x].value=="B": continue

						anc = old_pred_matrix[n_y][n_x]

						# probability of having transitioned from this ancestor
						cur_prob_given_anc = 0.0

						# cell above current cell
						if n_y==y-1:
							# if action was down
							if cur_action in ["Down","D"]: cur_prob_given_anc = 0.9
							else: 						   cur_prob_given_anc = 0.1

						# cell below current cell
						if n_y==y+1:
							if cur_action in ["Up","U"]: cur_prob_given_anc = 0.9
							else: 						 cur_prob_given_anc = 0.1

						# cell left of current cell
						if n_x==x-1:
							# if the action was right
							if cur_action in ["Right","R"]: cur_prob_given_anc = 0.9
							else:    					    cur_prob_given_anc = 0.1

						# cell right of current cell
						if n_x==x+1:
							# if the action was left
							if cur_action in ["Left","L"]: cur_prob_given_anc = 0.9
							else: 						   cur_prob_given_anc = 0.1

						# add cost of having transitioned from this possible ancestor
						total_anc_prob+=cur_prob_given_anc

						transition_matrix[y][x].parent_costs.append(cur_prob_given_anc)
						transition_matrix[y][x].parents.append(anc)

					# calculate probability of having stayed in the current location
					myself_prob_given_anc = 0.9 if condition_matrix[y][x].value==cur_reading else 0.1

					# if the reported action would not have been possible because the higher probability ancestor is a blocked cell
					if self.is_blocked_in_direction(x,y,cur_action): myself_prob_given_anc *= 0.9
					else: myself_prob_given_anc *= 0.1

					# add the probability of having stayed to total probability
					total_anc_prob+=myself_prob_given_anc

					# normalizing prob_given_anc values
					normalized_prob_given_anc = []
					anc = []

					# add a pointer back to the same location
					normalized_prob_given_anc.append(myself_prob_given_anc)
					anc.append(old_pred_matrix[y][x])

					# put all ancestors of the current x,y in the anc list,
					for i in range(len(transition_matrix[y][x].parents)):
						cur = transition_matrix[y][x].parents[i]
						cur_val = transition_matrix[y][x].parent_costs[i]
						normalized_prob_given_anc.append(cur_val)
						anc.append(cur)

					transition_matrix[y][x].parents = anc
					transition_matrix[y][x].parent_costs = normalized_prob_given_anc

					# figure out which parent has the highest transition probability
					#best_parent_transition = 0.0

					# figure out which is the best parent and set it
					best_parent_prob = 0.0

					for i in range(len(transition_matrix[y][x].parents)):
						cur_parent = transition_matrix[y][x].parents[i]
						cur_val = transition_matrix[y][x].parent_costs[i]

						if (cur_val*cur_parent.value)>best_parent_prob:
							best_parent_prob = cur_val*cur_parent.value
							transition_matrix[y][x].parent = cur_parent
					
					anc_prob_total = 0.0 # sum of P(x)*T(x) for all parents x

					# get the entire ancestor tree probability for this location
					for i in range(len(transition_matrix[y][x].parents)):
						cur_val = transition_matrix[y][x].parents[i].value
						cur_trans = transition_matrix[y][x].parent_costs[i]
						anc_prob_total += (cur_val*cur_trans)

					# probability of being in this spot given the reported reading
					this_spot_prob = 0.9 if condition_matrix[y][x].value==cur_reading else 0.1

					# multiply by the sum of all P(x-1)*alpha(x-1) for x-1 = ancestors of x where x = current location
					transition_matrix[y][x].value = this_spot_prob * anc_prob_total

		transition_matrix = self.normalize_matrix(transition_matrix)
		self.prediction_matrices.append(transition_matrix)

	# provided current action, checks if the current cell would have had to have come from a blocked cell
	def is_blocked_in_direction(self,x,y,action):
		x1,y1 = self.get_adjusted_coord(x,y,action)
		try: val = self.conditions_matrix[y1][x1].value
		except: return False # ancestor is out of bounds
		if val=="B": return True # ancestor is blocked
		return False # ancestor is open

	# returns the [x,y] of cell in the opposite of 'direction' if fwd is True,
	# otherwise returns the [x,y] of cell in 'direction' # fwd should be True
	def get_adjusted_coord(self,x,y,direction,fwd=False):
		if fwd:
			x1,y1 = x,y
			if direction in ["Left","L"]: 	x1+=  1
			if direction in ["Right","R"]: 	x1+= -1
			if direction in ["Up","U"]: 	y1+=  1
			if direction in ["Down","D"]: 	y1+= -1
			return x1,y1
		else:
			x1,y1 = x,y
			if direction in ["Left","L"]: 	x1+= -1
			if direction in ["Right","R"]: 	x1+=  1
			if direction in ["Up","U"]: 	y1+= -1
			if direction in ["Down","D"]: 	y1+=  1
			return x1,y1

	# creates a new matrix provided a prior prediction matrix and a transition matrix
	def resolve_prediction_matrix(self,transition_matrix,old_pred_matrix,ancestors=None):
		if ancestors==None:
			new_pred_matrix = []
			for y in range(self.num_rows):
				row = []
				for x in range(self.num_cols):
					new_node = viterbi_node()
					new_node.coords = [x,y]
					new_node.value = float(transition_matrix[y][x].value)*float(old_pred_matrix[y][x].value)
					new_node.parent = None
					row.append(new_node)
				new_pred_matrix.append(row)
			return new_pred_matrix
		else:
			new_pred_matrix = []
			for y in range(self.num_rows):
				row = []
				for x in range(self.num_cols):
					anc_x,anc_y = ancestors[y][x]

					new_node = viterbi_node()
					new_node.coords = [x,y]
					#new_node.parent = deepcopy(old_pred_matrix[anc_y][anc_x])
					new_node.parent = old_pred_matrix[anc_y][anc_x]
					anc_prob = new_node.parent.value
					#anc_prob = float(old_pred_matrix[anc_y][anc_x].value)
					new_node.value = float(transition_matrix[y][x].value)*anc_prob
					row.append(new_node)
				new_pred_matrix.append(row)
			return new_pred_matrix

	# returns the sum of all elements in input matrix
	def get_matrix_sum(self,matrix):
		matrix_sum = 0
		for y in range(len(matrix)):
			for x in range(len(matrix[y])):
				matrix_sum += float(matrix[y][x].value)
		return matrix_sum

	# divides each elements of the input matrix by its matrix sum
	def normalize_matrix(self,matrix):
		matrix_sum = float(self.get_matrix_sum(matrix))
		for y in range(len(matrix)):
			for x in range(len(matrix[y])):
				matrix[y][x].value = float(matrix[y][x].value)/matrix_sum
		return matrix

	# initializes the prediction matrix, iterates over provided observations
	# and updates weights at each step. If path is set to True the viterbi algorithm
	# will be called to analyze each step and output the most likely path taken
	def init_observations(self,seen_actions,seen_readings,path=False,print_ancestors=False,print_condition=True):

		# set global variables to assign execution state values
		self.print_prediction = True  			 #
		self.print_ancestors  = print_ancestors
		self.print_condition  = print_condition

		#self.transition_matrices = []
		self.init_conditions_matrix()

		self.observed_actions  = [] # filled in add_observation
		self.observed_readings = [] # ""

		if not path:
			sys.stdout.write("\nGrid Conditions...\n")
			self.print_matrix(self.conditions_matrix,3)

		self.move_index = 1
		self.print_current_state(6)

		for self.cur_action,self.cur_reading in zip(seen_actions,seen_readings):

			# add the observation
			self.add_observation()

			# update weights given the new information
			self.update_weights()

			# print out current state information
			self.print_current_state(8)

			if path:
				# get the current sequence
				pred_seq,pred_prob = self.get_predicted_sequence()

				# print out current sequence
				self.print_predicted_sequence(pred_seq,pred_prob)

		print("\nAll observations complete.\n")

	# pred_matrix: prediction matrix
	# current_location: [x,y] (x,y in [0,1,2]), current location
	#
	# return: [x,y] (x,y in [0,1,2]), coordinates of likely ancestor
	def get_ancestor(self,pred_matrix,current_location,last_action=None):
		highest_prob = 0
		ancestor = [-1,-1]
		possible_ancestors = self.get_neighbors(current_location)
		for x,y in possible_ancestors:
			val = pred_matrix[y][x].value
			if val>highest_prob:
				highest_prob = val
				ancestor = [x,y]
		return ancestor,highest_prob

	# pred_matrix: prediction matrix
	# current_location: [x,y] (x,y in [0,1,2]), current location
	#
	# return: [[x,y],...] list of neighbor indices
	def get_neighbors(self,current_location):
		possible_neighbors = []

		x0, y0 = current_location[0], current_location[1]

		x_operations = [1,-1,0]
		y_operations = [1,-1,0]

		for y in y_operations:
			for x in x_operations:
				possible_neighbors.append([x0+x,y0+y])

		neighbors = []
		for x,y in possible_neighbors:
			# ensure in bounds...
			if ((x>=0 and x<self.num_cols) and (y>=0 and y<self.num_rows)):
				if x!=x0 and y!=y0: continue # skip diagonal neighbors
				neighbors.append([x,y])
		return neighbors

	# pred_matrix: prediction matrix
	#
	# return: [x,y] (x,y in [0,1,2]), most likely current location
	def predict_location(self,pred_matrix,exclude=None):
		highest_prob = 0
		location 	 = [-1,-1]
		for y in range(len(pred_matrix)):
			for x in range(len(pred_matrix[y])):
				val = pred_matrix[y][x].value
				if (val>highest_prob):
					if exclude is not None and [x,y] in exclude: continue
					highest_prob = val
					location = [x,y]
		return location, highest_prob

	# pred_matrices: list of prediction matrices (1 for each reported action)
	#
	# return: [[x,y],...] list of predicted locations back to starting spot
	def get_predicted_sequence(self,score=False):

		last_location, last_probability = self.predict_location(self.prediction_matrices[-1])
		predicted_last_location = copy(last_location)

		best_path = []
		best_path.append(last_location)

		last_location = self.prediction_matrices[-1][last_location[1]][last_location[0]]

		path_prob = last_probability

		while True:
			last_location = last_location.parent
			if last_location == None: break
			new_coords = last_location.coords
			best_path.insert(0,new_coords)

		if score:
			a_x,a_y = self.actual_traversal_path[len(best_path)-2]
			score = abs(predicted_last_location[0]-a_x)+abs(predicted_last_location[1]-a_y)
			return [best_path[1:],[path_prob],score]
		return [best_path[1:],[path_prob]]

	# condition_matrix: condition matrix (strings)
	# predicted_seq: [[x,y],...] list of predicted locations
	#
	# prints out the path overlaid on the grid
	def print_predicted_sequence(self,predicted_seq,seq_probabilities):
		condition_matrix = self.conditions_matrix
		seen_actions     = self.observed_actions
		seen_readings    = self.observed_readings

		sys.stdout.write("\n Predicted Sequence: \n")
		seq_str = ""
		idx=0
		for a,b in predicted_seq:
			idx+=1
			if idx%6==0: sys.stdout.write("\n")
			sys.stdout.write(" ("+str(a)+","+str(b)+")")
		sys.stdout.write("\n\n")

		# 9 total rows in predicted sequence diagram
		rows = []
		for i in range(3*self.num_rows):
			rows.append("")

		# row above the sequence digram (see state_header_str below)
		actions = []

		# create string to represent the x axis of the plot (horizontal, top of plot)
		x_axis = "      "
		#for i in range(len(seq_probabilities)):
		if True:
			for i in range(self.num_cols):
				item = str(i)
				left = True
				while len(item)<5:
					if left:
						left = False
						item = " "+item
					else:
						left = True
						item += " "
				x_axis += item
			x_axis += "    "

		# to know if we have covered each location on the sequence
		rendered_node = [0] * len(predicted_seq)

		# print out state matrix with a single location ( ) denoting current spot, appended onto
		# whatever we have so far in the rows[] array (any previous state matrices, iterations)
		for y in range(self.num_rows):

			above_row = ""
			below_row = ""
			full_row = ""

			for x in range(self.num_cols):

				above_section = "     "
				below_section = "     "

				above_section = list(above_section)
				below_section = list(below_section)

				cur_cond = condition_matrix[y][x].value
				row = "  "+cur_cond+"  "

				row = list(row)

				if [x,y] in predicted_seq:
					i = predicted_seq.index([x,y])
					skip = False

					if rendered_node[i]==1:
						i+=1
						while True:
							if i==len(predicted_seq):
								skip = True
								break
							if x==predicted_seq[i][0] and y==predicted_seq[i][1]:
								if rendered_node[i]==0:
									rendered_node[i] = 1
									skip = False
									break
							i+=1

					last_loc = None
					next_loc = None

					if not skip:
						if i>0:          			last_loc = predicted_seq[i-1] # if there was an earlier element in sequence
						if i<len(predicted_seq)-1:  next_loc = predicted_seq[i+1] # if there is another element in sequence

					if last_loc is not None:
						# if the prior location was in the same column
						if last_loc[0]==x:
							# if the prior location was in the above neighbor
							if last_loc[1]==y-1:
								above_section[2] = '|'
								#need_above = True
							# if the prior location was in the below neighbor
							elif last_loc[1]==y+1:
								below_section[2] = '^'
								#need_below = True

						# if the prior location was in the same row
						elif last_loc[1]==y:
							# if the prior location was in the left neighbor
							if last_loc[0]==x-1: row[0],row[1] = '-','>'
							# if the prior location was in the right neighbor
							if last_loc[0]==x+1: row[3],row[4] = '<','-'

					if next_loc is not None:
						# if the next location is in the same column
						if next_loc[0]==x:
							# if the next location is in the above neighbor
							if next_loc[1]==y-1:
								above_section[2] = '|'
							# if the next location is in the below neighbor
							elif next_loc[1]==y+1:
								below_section[2] = 'v'
								#need_below = True

						# if the next location is in the same row
						elif next_loc[1]==y:
							# if the next location is in the left neighbor
							if next_loc[0]==x-1: row[0],row[1] = '<','-'
							# if the next location is in the right neighbor
							if next_loc[0]==x+1: row[3],row[4] = '-','>'

					if predicted_seq[len(predicted_seq)-1] == [x,y]:
						row[1] = '('
						row[3] = ')'

					if predicted_seq[0] == [x,y]:
						row[1] = '['
						row[3] = ']'

					#del predicted_seq[i]

				above_section = "".join(above_section)
				below_section = "".join(below_section)
				row = "".join(row)

				above_row += above_section
				full_row  += row
				below_row += below_section

			rows[3*y]   += above_row
			rows[3*y+1] += full_row
			rows[3*y+2] += below_row

		horizontal_delim = ''.join("_" for _ in range(5*self.num_cols))
		sys.stdout.write(x_axis)
		sys.stdout.write("\n      "+horizontal_delim+"\n")

		# write out the path displays
		for i in range(1,3*self.num_rows-1):
			if (i+2)%3==0:
				item = " "+str(int(i/3))
				while len(item)<4:
					item+=" "
				#sys.stdout.write(item+"|")
			else:
				item = ""
			while len(item)<5:
				item = " "+item
			item += "|"
			sys.stdout.write(item)
			sys.stdout.write(rows[i]+"|"+"\n")

		sys.stdout.write("      "+horizontal_delim)
		sys.stdout.write("\n")

		sys.stdout.write("\n Seq. Probability: ")
		sys.stdout.write(str(seq_probabilities[-1])[:8])
		sys.stdout.write("\n")

	# writes out to specified device
	def _write_single_sequence(self,sequence,print_seq=True,device=None):
		if print_seq:
			device.write("\n ")
			seq_str = ""
			idx=0
			for a,b in sequence:
				idx+=1
				if idx%6==0: device.write("\n")
				device.write(" ("+str(a)+","+str(b)+")")

			#device.write("  "+" ".join("["+str(a)+","+str(b)+"]" for [a,b] in sequence))
			#device.write("\n\n")

		device.write("\n")

		# create x axis to print above plot
		x_axis = ""
		for i in range(self.num_cols):
			item = str(i)
			left = True
			while len(item)<5:
				if left:
					left = False
					item = " "+item
				else:
					left = True
					item += " "
			x_axis += item
		device.write("        "+x_axis+"\n")

		x_axis_divider = "".join("_" for _ in range(5*self.num_cols))
		device.write("      "+x_axis_divider+"\n")

		condition_matrix = self.conditions_matrix

		rows = []
		for i in range(3*self.num_rows):
			rows.append("")

		# make shallow copy of the predicted sequence (a list of [x,y] coordinates)
		seq = copy(sequence)

		# to know if we have covered each location on the sequence
		rendered_node = [0] * len(sequence)

		# if a row has no contents, don't write it out at end
		empty_rows = [False] * (3*self.num_rows)

		# print out state matrix with a single location ( ) denoting current spot, appended onto
		# whatever we have so far in the rows[] array (any previous state matrices, iterations)
		for y in range(self.num_rows):

			above_row = "" # row printed above current element row
			below_row = "" # row printed below current element row
			full_row  = "" # row holding current element row
			need_above = False # if we don't place anything in the above_row
			need_below = False # if we don't place anything in the below_row

			for x in range(self.num_cols): # iterate over each element in current row

				above_section = "     " # substring of above_row (to be appended)
				below_section = "     " # substring of below_row (to be appended)

				above_section = list(above_section)
				below_section = list(below_section)

				cur_cond = condition_matrix[y][x].value
				row = "  "+cur_cond+"  " # add the current element
				row = list(row)

				if [x,y] in seq: # if this spot is in the traversal sequence

					i = seq.index([x,y])
					skip = False

					if rendered_node[i]==1:
						i+=1
						while True:
							if i==len(seq):
								skip = True
								break
							if x==seq[i][0] and y==seq[i][1]:
								if rendered_node[i]==0:
									rendered_node[i] = 1
									skip = False
									break
							i+=1

					last_loc = None
					next_loc = None

					if not skip:
						if i>0:          last_loc = seq[i-1] # if there was an earlier element in sequence
						if i<len(seq)-1: next_loc = seq[i+1] # if there is another element in sequence

					if last_loc is not None:
						# if the prior location was in the same column
						if last_loc[0]==x:
							# if the prior location was in the above neighbor
							if last_loc[1]==y-1:
								above_section[2] = '|'
								need_above = True
							# if the prior location was in the below neighbor
							elif last_loc[1]==y+1:
								below_section[2] = '^'
								need_below = True

						# if the prior location was in the same row
						elif last_loc[1]==y:
							# if the prior location was in the left neighbor
							if last_loc[0]==x-1: row[0],row[1] = '-','>'
							# if the prior location was in the right neighbor
							if last_loc[0]==x+1: row[3],row[4] = '<','-'

					if next_loc is not None:
						# if the next location is in the same column
						if next_loc[0]==x:
							# if the next location is in the above neighbor
							if next_loc[1]==y-1:
								above_section[2] = '|'
								need_above = True
							# if the next location is in the below neighbor
							elif next_loc[1]==y+1:
								below_section[2] = 'v'
								need_below = True

						# if the next location is in the same row
						elif next_loc[1]==y:
							# if the next location is in the left neighbor
							if next_loc[0]==x-1: row[0],row[1] = '<','-'
							# if the next location is in the right neighbor
							if next_loc[0]==x+1: row[3],row[4] = '-','>'

					# if the final destination
					if seq[len(seq)-1] == [x,y]:
						row[1] = '('
						row[3] = ')'

					# if the starting location
					if seq[0] == [x,y]:
						row[1] = '['
						row[3] = ']'


				above_section = "".join(above_section) # turn list to string
				below_section = "".join(below_section) # turn list to string
				row = "".join(row) # turn list to string

				# add items to this rows' above, below, and full row attributes
				above_row += above_section
				full_row  += row
				below_row += below_section



			rows[3*y]   += above_row
			rows[3*y+1] += full_row
			rows[3*y+2] += below_row

			if need_above==False: empty_rows[3*y] = True # if we never put anything in above_row
			if need_below==False: empty_rows[3*y+2] = True # if we never put anything in below_row

		# print out all nonempty rows
		for i in range(3*self.num_rows):
			if not empty_rows[i]:
				if (i+2)%3 == 0:
					item =" "+str(int(i/3))
					while len(item)<5:
						item += " "
				else:
					item = "     "
				item += "|  "
				print_row = item+rows[i]
				device.write(print_row+"\n")
		device.write("\n")

	# prints a copy of the conditions_matrix with the provided sequence overlaid
	def print_single_sequence(self,sequence,print_seq=True):
		self._write_single_sequence(sequence,print_seq,sys.stdout)

	# writes out to specified device
	def _write_matrix(self,matrix,desired_item_size=20,device=None):
		x_axis = ""
		for i in range(self.num_cols):
			item = str(i)
			left = True
			while len(item)<desired_item_size+3:
				if left:
					left = False
					item = " "+item
				else:
					left = True
					item += " "
			x_axis += item
		device.write("      "+x_axis+"\n")

		delim_line = ''.join("_" for _ in range(self.num_cols*(desired_item_size+3)))
		#delim_line = delim_line
		device.write("      "+delim_line[:len(delim_line)-1]+"\n")

		idx = -1
		for row in matrix:
			idx+=1
			before = "  "+str(idx)
			while len(before)<5:
				before+=" "
			device.write(before+"| ")
			for item in row:

				# if just a string entry
				if str(item.value)==item.value:
					real_item_size = len(str(item.value))
					device.write(str(item.value)[:desired_item_size])
				# if a float entry, write out formatted
				else:
					real_item_size = desired_item_size
					output_str = "%0."+str(desired_item_size-2)+"f"
					device.write(output_str % item.value)

				if real_item_size<desired_item_size:
					for _ in range(desired_item_size-real_item_size):
						device.write(" ")

				if row.index(item) is not len(row)-1:
					device.write(" | ")
				else:
					device.write(" |")
			if matrix.index(row) is not len(matrix)-1:
				device.write("\n     |"+delim_line[:len(delim_line)-1]+"|\n")
			else:
				device.write("\n     |"+delim_line[:len(delim_line)-1]+"|\n")

	# desired_item_size: column width in characters
	#
	# prints out either a prediction or condition matrix
	def print_matrix(self,matrix,desired_item_size=20):
		self._write_matrix(matrix,desired_item_size,device=sys.stdout)

	# saves ancestor information to specified device id
	def save_anc_info(self,iteration,device):
		self._write_anc_info(iteration,device)

	# writes out to a specified device
	def _write_anc_info(self,iteration=None,device=None):
		if iteration is not None:
			device.write("\n\n  x,y  |    Ancestor Information (Iteration "+str(iteration)+") \n")
		else:
			device.write("\n\n  x,y  |    Ancestor Information \n")

		for y in range(self.num_rows):
			for x in range(self.num_cols):
				parents_str = ""

				if len(self.prediction_matrices[-1][y][x].parents)==0: continue

				for a in self.prediction_matrices[-1][y][x].parents:
					a_x, a_y = a.coords
					cur_parents_str = "("+str(a_x)+","+str(a_y)+")"
					while len(cur_parents_str)<10:
						cur_parents_str+=" "
					parents_str += cur_parents_str

				parents_trans_str = ""
				for a in self.prediction_matrices[-1][y][x].parent_costs:
					parents_trans_str+= "%0.6f" % a
					parents_trans_str+= "  "

				parents_values_str = ""
				for a in self.prediction_matrices[-1][y][x].parents:
					val = a.value
					parents_values_str += "%0.6f" % val
					parents_values_str += "  "

				cur_header = " ("+str(x)+","+str(y)+")"
				cur_header_space = "".join(" " for _ in range(len(cur_header)))

				device.write(cur_header+" value:   %0.6f\n"%self.prediction_matrices[-1][y][x].value)
				device.write(cur_header_space+" parents: "+parents_str+"\n")
				device.write(cur_header_space+" tvalues: "+parents_trans_str+"\n")
				device.write(cur_header_space+" pvalues: "+parents_values_str+"\n\n")

	# calls _write_anc_info with sys.stdout as the device 
	def print_anc_info(self):
		self._write_anc_info(self.move_index-1,sys.stdout)

	# prints out information about the current step, i.e. the current
	# condition matrix (doesn't change over steps), the current prediction
	# matrix (adjusted on each step), the current reported action, and the
	# current reported reading
	def print_current_state(self,desired_item_size=20):

		pred_matrix 	 = self.prediction_matrices[-1] # get the last prediction matrix
		condition_matrix = self.conditions_matrix # get the condition matrix

		delim_line = ''.join("=" for _ in range((self.num_cols+5)*(desired_item_size)))
		if self.move_index==1:
			print("\n"+delim_line+"\n")#+delim_line)
			print(" Initial State")
		else:
			print("\n"+delim_line+"\n")#+delim_line)
			print(" Move Index:\t\t"+str(self.move_index-1))
			print(" Reported Action:\t("+str(self.cur_action)+", "+str(self.cur_reading)+")")

		if condition_matrix is not None and self.print_condition:
			sys.stdout.write("\n Condition Matrix:\n")
			self.print_matrix(condition_matrix,desired_item_size)

		if len(self.prediction_matrices)!=0 and self.print_ancestors:
			self.print_anc_info()

		if self.temp_anc_matrix is not None and self.display_temp_ancestor_matrix:
			print("\n Ancestors Matrix: ")
			self.print_matrix(self.temp_anc_matrix,desired_item_size)

		if pred_matrix is not None and self.print_prediction:
			sys.stdout.write("\n\n Current Probability Matrix:\n")
			self.print_matrix(pred_matrix,desired_item_size)

		if self.actual_traversal_path!=None and self.print_actual_traversal:
			if self.move_index!=1 and not self.print_full_traversal:
				sys.stdout.write("\n Current ACTUAL Agent Traversal (trimd. to length of predicted)...\n")
				if len(self.actual_traversal_path)<=self.current_predicted_length+1:
					print_seq = self.actual_traversal_path
				else:
					print_seq = self.actual_traversal_path[:self.current_predicted_length+1]
				self.print_single_sequence(print_seq)
			else:
				sys.stdout.write("\n Full ACTUAL Agent Traversal Path { end=(), start=[] }...\n")
				self.print_single_sequence(self.actual_traversal_path)
