#!/usr/bin/python

import sys

import fileio
import collapse
import latexifier
import quantlex

inputFile = ""
outputFile = ""
inputText = ""
outputText = ""

def showUsage():
	print """Usage: collapser <INPUT> <OUTPUT> options"""


# Pre-latexifier.
def postLatexSanityCheck(text):
	# Look for unexpected characters etc. here
	pos = text.find('_')
	if pos is not -1:
		raise ValueError("Found invalid underscore '_' character on line %d:\n%s" % (quantlex.find_line_number(text, pos), quantlex.find_line_text(text, pos)) )
	return

def main():

	print """Collapser 0.1"""

	if len(sys.argv) != 3:
		showUsage()
		sys.exit()

	inputFile = sys.argv[1]
	outputFile = sys.argv[2]

	files = []
	inputText = fileio.readInputFile(inputFile)
	if inputFile[-12:] == "manifest.txt":
		path = inputFile[:-12]
		print "Reading manifest '%s'" % inputFile
		files = fileio.loadManifest(path, inputText)
	else:
		print "Reading file '%s'" % inputFile
		files = [inputText]

	# print "Here is the input:\n%s" % inputText

	collapsedTexts = []
	for file in files:
		collapsedTexts.append(collapse.go(file))

	collapsedText = ''.join(collapsedTexts)

	outputText = latexifier.go(collapsedText)

	postLatexSanityCheck(outputText)


	# print "\n\nHere is the output:\n%s" % outputText

	fileio.writeOutputFile(outputFile, outputText)



main()
