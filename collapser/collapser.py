#!/usr/bin/python

import sys
import getopt

import fileio
import collapse
import latexifier
import quantlex
import chooser

inputFile = ""
outputFile = ""
inputText = ""
outputText = ""

latexBegin = "fragments/begin.tex"
latexEnd = "fragments/end.tex"
latexFrontMatter = "fragments/frontmatter.tex"
latexPostFrontMatter = "fragments/postfrontmatter.tex"



def latexWrapper(text, includeFrontMatter=True):
	begin = fileio.readInputFile(latexBegin)
	end = fileio.readInputFile(latexEnd)
	frontMatter = fileio.readInputFile(latexFrontMatter)
	postFrontMatter = fileio.readInputFile(latexPostFrontMatter)
	output = begin
	if includeFrontMatter:
		output += frontMatter
	output += postFrontMatter
	output += text
	output += end
	return output



# Pre-latexifier.
def postLatexSanityCheck(text):
	# Look for unexpected characters etc. here
	pos = text.find('_')
	if pos is not -1:
		raise ValueError("Found invalid underscore '_' character on line %d:\n%s" % (quantlex.find_line_number(text, pos), quantlex.find_line_text(text, pos)) )
	return


def showUsage():
	print """Usage: collapser -i <INPUT> -o <OUTPUT> options"""


def main():

	print """Collapser 0.1"""

	opts, args = getopt.getopt(sys.argv[1:], "i:o:", ["help"])
	print opts
	print args
	if len(args) > 0:
		print "Unrecognized arguments: %s" % args
		sys.exit()
	for opt, arg in opts:
		if opt == "-i":
			inputFile = arg
		elif opt == "-o":
			outputFile = arg
		elif opt == "--help":
			print "Help."
			showUsage()
			sys.exit()

	if inputFile == "" or outputFile == "":
		print "Missing input or output file."
		showUsage()
		sys.exit()

	seed = chooser.number(10000000)
	chooser.setSeed(seed)
	print "Seed (random): %d" % seed

	files = []
	inputText = fileio.readInputFile(inputFile)
	if inputFile[-12:] == "manifest.txt":
		path = inputFile[:-12]
		print "Reading manifest '%s'" % inputFile
		files = fileio.loadManifest(path, inputText)
	else:
		print "Reading file '%s'" % inputFile
		files = [inputText]

	fileTexts = []
	for file in files:
		fileTexts.append(file)
	joinedFileTexts = ''.join(fileTexts)
	collapsedText = collapse.go(joinedFileTexts)

	outputText = latexifier.go(collapsedText)

	postLatexSanityCheck(outputText)

	outputText = latexWrapper(outputText, includeFrontMatter=False)	

	fileio.writeOutputFile(outputFile, outputText)



main()
