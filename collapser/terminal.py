# Abstraction over various terminal file i/o operations used during generation of books: moving, renaming, deleting files etc. Designed to run on the author's Mac OS install circa 2020; likely to need adjustments to work in other environments.

import shlex
import subprocess
import re
import sys

def runCommand(command, paramString, shell=False):
	if shell:
		cmdArray = "%s %s" % (command, paramString)
	else:
		cmdArray = shlex.split(paramString)
		cmdArray.insert(0, command)

	result = {
		"success": False,
		"output": ""
	}

	try:
		print "About to run '%s'" % cmdArray
		output = subprocess.check_output(cmdArray, stderr=subprocess.STDOUT, shell=shell)
		result["success"] = True
		result["output"] = output
	except subprocess.CalledProcessError as e:
		result["success"] = False
		result["output"] = e.output

	return result


def rename(input, output):
	runCommand("mv", input + " " + output)

def delete(fn, isDir = False):
	if isDir:
		runCommand("rm", "-r %s" % fn)
	else:
		runCommand("rm", fn)

def move(input, output):
	print "Moving %s to %s." % (input, output)
	runCommand("mv", input + " " + output)

def zip(inputFiles, output, removeAfter = False):
	fileList = " ".join(inputFiles)
	# -j means don't include directories in the zip file
	# -X means don't include Mac OS junk files
	paramString = "-j -X %s %s" % (output, fileList)
	runCommand("zip", paramString)
	if removeAfter:
		for file in inputFiles:
			delete(file)
