#!/usr/bin/python

#'"When you dig a well, there's no sign of water until you reach it, only rocks and dirt to move out of the way. You have removed enough; soon the pure water will flow," said Buddha.' - Deepak Chopra

#Chopra 1.0 - port of ShuffleUnpack to Python, more or less

from sys import argv, exit
import os, os.path
import io
from binascii import hexlify
from struct import unpack_from as unpack
import tempfile
import re
import zipfile
import string

magic_decryption = "\xD2\x06\x6F\xC6\x70\xD2\xB3\xA8\x9C\x0B\x5B\xE3\x49\xF6\xA4\xDE"

def binxor(binIn, magicnum):
	magic = [ord(byte) for byte in magicnum]
	mod = len(magicnum)
	out = ""
	for index, byte in enumerate(binIn):
		out += chr(ord(byte) ^ magic[index % mod])
	return out


### DATA CONVERSION FUNCTIONS

def read_short(file,start=None):
	#archive files use LITTLE endianness
	global file_pointer
	if start is None:
		start = file_pointer
		file_pointer += 2
	return unpack("<H",file[start:start+2])[0]
		
	
def read_signed_short(file,start=None):
	global file_pointer
	if start is None:
		start = file_pointer
		file_pointer += 2
	return unpack("<h",file[start:start+2])[0]

def read_int(file,start=None):
	global file_pointer
	if start is None:
		start = file_pointer
		file_pointer += 4
	return unpack("<I",file[start:start+4])[0]
	
def as_signed_int(file,start=None):
	global file_pointer
	if start is None:
		start = file_pointer
		file_pointer += 4
	return unpack("<i",file[start:start+4])[0]

def read_hexname(file,start=None):
	global file_pointer
	if start is None:
		start = file_pointer
		file_pointer += 4
	return string.upper(hexlify(file[start:start+4][::-1])) #the [::-1] swaps the bytes - endianness!
	
def read_data(file,lenR,start=None):
	global file_pointer
	if start is None:
		start = file_pointer
		file_pointer += lenR
	return file[start:start+lenR]

def write_data(file,data,start=None):
	#overwrites data in a binary string.
	global file_pointer
	lenW = len(data)
	if start is None:
		start = file_pointer
		file_pointer += lenW
	if start+lenW > len(file):
		print "Warning: A write extends the length of this data."	
	return file[:start]+data+file[start+lenW:]


if len(argv) < 2:
	print "Sorry, I need a file or folder path to unpack."
	exit(1)
	
if not os.access(argv[1], os.R_OK):
	print "I can't read the file path you've given me (or it isn't a path at all)."
	exit(1)

isdir = os.path.isdir(argv[1])

if isdir:
	files_to_check = os.listdir(argv[1])
else:
	files_to_check = list(argv[1])

#set up name dictionaries
filenames = {}
arcnames = {}
regionnames = {}
mystery_filenames = {}

try:
	with open("File Names.txt") as filenames_file:
		for line in filenames_file:
			subline = line.strip().split("\t")
			filenames[subline[0]] = subline[1]
	
	with open("Message Regions.txt") as filenames_file:
		for line in filenames_file:
			subline = line.strip().split("\t")
			regionnames[subline[0]] = subline[1]
		
	with open("Archive Names.txt") as filenames_file:
		for line in filenames_file:
			subline = line.strip().split("\t")
			arcnames[subline[0]] = subline[1]
except IOError:
	print "I need my data files - File Names.txt, Message Regions.txt, and Archive Names.txt - in the current directory for the files to be properly named. Stopping now."
	exit(1)

#set up output dir	
try:
	os.mkdir("output_mobile") #make output dir, fail silently if it's already here.	
except OSError:
	pass
	
	
#check file / files in folder	
for file in files_to_check:
	origfilename = file
	if isdir:
		file = argv[1]+"/"+file #add directory before path

	if os.path.isdir(file):
		print "File '"+file+"' is a directory. Skipping."
		continue
	
	if not os.access(file, os.R_OK):
		print "I can't read file '"+file+"'. Skipping."
		continue

	shuffle_file = b""	
		
	with io.open(file, mode='rb') as shuffle_file_ptr:
		shuffle_file = shuffle_file_ptr.read() #read whole file

	file_pointer = 0 #global - acts as 'file pointer' when reading
	
	#validate the contents
	#We're looking for the magic number to see if this is a REAL archive file.
	extra_offset = 0 #set to 256 if this is an ExtData archive.
	front_offset = 0

	magic = read_int(shuffle_file)
	if magic != 13:
		extra_offset = 256 #skip RSA signature from hereon
		file_pointer = 256
		
		magic = read_int(shuffle_file)
		if magic != 13: #0x000D
			print magic
			print "File '"+file+"' doesn't look like a valid archive file. Skipping."
			continue
	#Continuing the magic number check, the next bytes spell out the name of the file! 
	
	magic_name = read_hexname(shuffle_file)
	
	
	if origfilename != magic_name:
		print "File '"+file+"' internal name doesn't match filename. This probably isn't a valid archive file. Skipping."
		print magic_name
		continue
		
	print "Unpacking file '"+file+"'."
	
	os.chdir("output_mobile/")
	
	try:
		this_file_dir_name = arcnames[origfilename]
		os.mkdir(arcnames[origfilename]) #make output dir, fail silently if it's already here.	
	except OSError:
		pass
	except KeyError:
		print "Couldn't find a folder name for file '"+origfilename+"'."
		try:
			this_file_dir_name = origfilename
			os.mkdir(origfilename)
		except OSError:
			pass
	
	
	
	#the next two ints are unknowns.
	file_pointer += 8
		
	#now we can start actually reading the file!
	num_packed_files = read_int(shuffle_file)
	padding_size = read_int(shuffle_file) #this is never USED in the unpacker, suggesting it's usually 0.
	
	#if padding_size > 0:
	#	print "Note: Padding size of this archive is greater than 0. If you get gibberish out the other end or the extraction fails, please send the offending file to SoItBegins."
	#it's always nonzero on mobile
	
	#a note on how big we expect this header block to be:
	#magic (4) + magicname (4) + two unknowns (8) + # packed files (4) + padding size (4) +, for EACH packed file:
	# (name hash (4) + unknown (4) + file length (4) + file offset (4) + 16 more unknown bytes) = 32 bytes for EACH packed file.
	#so that's 24 + 32 * packed files.
	
	front_offset = 24 + 32*num_packed_files
	
	packed_file_info = []
	
	for fileno in range(num_packed_files):
		name_hash = read_hexname(shuffle_file)
		file_pointer += 4 #the original unpacker code is awfully vague on what the next int is supposed to be, too.
		file_length = read_int(shuffle_file)
		file_offset = read_int(shuffle_file)
		packed_file_info.append([name_hash, file_length, file_offset])
		file_pointer += 16 #skip the next 16 bytes.
		
	#once we have the information, the next step is to unzip and decode everything inside the archive.
	
	
	for packed_file in packed_file_info:
		name_hash, file_length, file_offset = packed_file
		print name_hash
	
		if name_hash in filenames.keys():
			real_file_name = filenames[name_hash]
			if "{0}" in real_file_name:
				try:
					real_file_name = real_file_name[:-7]+regionnames[origfilename]+real_file_name[-4:]
				except:
					real_file_name = real_file_name[:-7]+"??"+real_file_name[-4:]
			
			print "Unpacking subfile '"+real_file_name+"' ("+name_hash+")."
		else:
			print "Couldn't find a name for packed subfile '"+name_hash+"'."
			if name_hash in mystery_filenames:
				mystery_filenames[name_hash] += 1
			else:
				mystery_filenames[name_hash] = 1
			real_file_name = name_hash
			
		#We can use the starting point and the length to feed this whole business to ZipFile.
			
		thisZip = tempfile.TemporaryFile()
		file_pointer = file_offset+extra_offset
		thisZipData = read_data(shuffle_file,file_length)
		
		#before we write all this fine data, we need to do a little quick fixing. The files listed are perfectly normal ZIP files, but they may not have names.
		#we need to find all the central directory and local file listings in the zipfile - we can do this quickly with re.finditer.
		
		num_subfiles = read_short(thisZipData, start=re.search("PK\x05\x06",thisZipData).start()+10)
		
		locals = re.finditer("PK\x03\x04",thisZipData)
		centrals = re.finditer("PK\x01\x02",thisZipData)
		file_names = []
		equiv_file_names = []
		
		try:
			for subfile_id in range(num_subfiles):
				this_local_pos = locals.next().start() + 26
				this_central_pos = centrals.next().start() + 28
				
				#get lengths of file name space we have available - this keeps us from writing over something we shouldn't
				local_file_name_len = read_short(thisZipData,start=this_local_pos)
				central_file_name_len = read_short(thisZipData,start=this_central_pos)
				
				if local_file_name_len != central_file_name_len:
					file_name_len = min(local_file_name_len,central_file_name_len)
					print "Note: Local file name length allotment and central file name length allotment do not match."				
				else:
					file_name_len = central_file_name_len
					
				equiv_file_names.append(real_file_name)
				real_file_name = real_file_name[:file_name_len] #truncate length of name about to be written if need be				
				file_names.append(real_file_name)
				
				#now actually write the names
				thisZipData = write_data(thisZipData,real_file_name, start=this_local_pos+4)
				thisZipData = write_data(thisZipData,real_file_name, start=this_central_pos+18)
				
		except StopIteration:
			#this would happen if there was a central directory entry not attached to an associated local... or vice versa.
			print "This subfile contains malformed archive data. Please send the offending file to SoItBegins. Moving on..."
			continue
		
		
		#actually extract the data now
		thisZip.write(thisZipData)
		thisZipFile = zipfile.ZipFile(thisZip, 'r')
		
		#decode! Mobile files are XOR-encoded. IDK why.
		for index, fileToDecode in enumerate(file_names):
			bamxor = thisZipFile.read(fileToDecode)
			bamout = binxor(bamxor,magic_decryption)
						
			with io.open(this_file_dir_name+"/"+equiv_file_names[index],'wb') as file:
				file.write(bamout)			
		
	os.chdir("..")		
	
if len(mystery_filenames.keys()) > 0:
	
	print "Extraction complete. Mystery file names:"
	mysterystring = ""
	first = True
	for key in sorted(mystery_filenames.keys()):
		if not first:
			mysterystring += ", "
		else:
			first = False
		if mystery_filenames[key] > 1:
			mysterystring += ( key +" ("+str(mystery_filenames[key])+" times)" )
		else:
			mysterystring += key
	
	print mysterystring

else:
	print "Extraction complete."