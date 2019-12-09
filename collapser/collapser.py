#!/usr/bin/python
# coding=utf-8

# TODO: Make an abstraction that holds the tokens for the book and rendered text in parallel, so you can say "show me the rendered text(s) for this particular control sequence", interrogate the control sequence at a specific position in the rendered text, etc.

# TODO: Proof 01915 has Part 3 starting on the wrong page. 

# TODO: Need to address the problem of authoring [DEFINE @A|@B], writing [A>text1|text2] somewhere, and then adding a @C and not catching the new edge case. On the one hand we ideally want to support [A>|] as a generic "else" clause (see @ffset vs the two tube options), but I'm really worried this will lead to a mistake slipping through. (The other version is also a problem, if we have [A>text1|B>text2], still printing nothing in the case of C.)

# TODO: add a sanity check for missing end punctuation, a la "ending Then". How to distinguish this from "following Niko" or "the Grapple" or "of Dhalgren"?

import sys
import getopt
import re

import fileio
import collapse
import quantlex
import quantparse
import chooser
import result
import differ
import hasher
import renderer_latex
import renderer_text
import renderer_html
import renderer_markdown
import renderer_epub
import renderer_mobi
import renderer_tweet

outputDir = "output/"
alternateOutputFile = outputDir + "alternate"
collapsedFileName = outputDir + "collapsed.txt"



def showUsage():
	print """Usage: collapser -o <OUTPUT_KEY> options
Arguments:
  --help         Show this message
  --front		 Include frontmatter
  --seed=x       Use the given integer as a seed
  --seed=random  Don't use an incremental seed; use one purely at random.
  --output=x	 Format to output (default none)
  				 "pdf" (for POD), "pdfdigital" (for online use),
  				 "txt", "html", "md", "epub", "mobi", "tweet"
  --noconfirm	 Skip variant confirmation
  --strategy=x   Selection strategy.
  		N		 Make N copies with "random" strategy
  		"random": default
  		"skipbanned": random, but avoid banned alternatives
  		"author": Author's preferred
  		"pair": Two versions optimizing for difference
  		"longest"
  		"shortest"
  --input=		 An alternate manifest file to load (default: full-book-manifest.txt)
  --only=x,y,z	 A list of files to render from the set loaded. 
  --set=x,y,z	 A list of variables to set true for this run.
                 Preface with ^ to negate
  --discourseVarChance=x   Likelihood to defer to a discourse var (default 80)
  --pickAuthorChance=x		Likelihood to pick author-preferred at random
  --skipPadding		Skip padding to 232 pages
  --skipEndMatter	Don't add end matter in padding
"""


def main():

	print """Collapser\n"""

	inputFiles = ["full-book-manifest.txt"]
	inputFileDir = "chapters/"
	outputFile = ""
	inputText = ""
	outputText = ""
	seed = -1
	strategy = "random"
	outputFormat = ""
	doFront = False
	doConfirm = True
	setDefines = []
	discourseVarChance = 80
	preferenceForAuthorsVersion = 20
	skipPadding = False
	skipEndMatter = False
	randSeed = False
	isDigital = False
	copies = 1
	onlyShow = []

	VALID_OUTPUTS = ["pdf", "pdfdigital", "txt", "html", "md", "epub", "mobi", "tweet", "none"]

	opts, args = getopt.getopt(sys.argv[1:], "o:", ["help", "seed=", "strategy=", "output=", "noconfirm", "front", "set=", "discourseVarChance=", "pickAuthorChance=", "skipPadding", "skipEndMatter", "input=", "only="])
	if len(args) > 0:
		print "Unrecognized arguments: %s" % args
		sys.exit()
	for opt, arg in opts:
		if opt == "--input":
			inputFiles = arg.split(',')
		elif opt == "-o":
			if len(re.findall(r"(\/|(\.(pdf|tex|txt)))", arg)) > 0:
				print "Please do not include paths or file extensions in output file (use --output to specify format)."
				sys.exit()
			outputFile = arg
		elif opt == "--help":
			print "Help."
			showUsage()
			sys.exit()
		elif opt == "--seed":
			if arg == "random":
				randSeed = True
			else:
				try:
					seed = int(arg)
				except:
					print "Invalid --seed parameter '%s': not an integer." % arg
					sys.exit()
		elif opt == "--strategy":
			try:
				copies = int(arg)
				strategy = "random"
			except:
				if arg not in quantparse.ParseParams.VALID_STRATEGIES:
					print "Invalid --strategy parameter '%s': must be one of %s" % (arg, quantparse.ParseParams.VALID_STRATEGIES)
				strategy = arg
		elif opt == "--output":
			if arg != "" and arg not in VALID_OUTPUTS:
				print "Invalid --output parameter '%s': must be one of %s" % (arg, VALID_OUTPUTS)
			if arg == "pdfdigital":
				arg = "pdf"
				isDigital = True
			outputFormat = arg
			if arg == "none":
				outputFormat = ""
		elif opt == "--noconfirm":
			doConfirm = False
		elif opt == "--front":
			doFront = True
		elif opt == "--set":
			setDefines = arg.split(',')
		elif opt == "--only":
			onlyShow = arg.split(',')
			print "Setting onlyShow: %s" % onlyShow
		elif opt == "--discourseVarChance":
			try:
				discourseVarChance = int(arg)
			except:
				print "Invalid --discourseVarChance parameter '%s': not an integer." % arg
				sys.exit()
		elif opt == "--pickAuthorChance":
			try:
				preferenceForAuthorsVersion = int(arg)
			except:
				print "Invalid --pickAuthorChance parameter '%s': not an integer." % arg
				sys.exit()
		elif opt == "--skipPadding":
			skipPadding = True
		elif opt == "--skipEndMatter":
			skipEndMatter = True

	if outputFile == "":
		print "*** Missing output file. ***\n"
		showUsage()
		sys.exit()

	if seed is not -1 and strategy is not "random" and strategy is not "skipbanned":
		print "*** You set seed to %d but strategy to '%s'; a seed can only be used when strategy is 'random' or 'skipbanned' ***\n" % (seed, strategy)
		sys.exit()

	if seed is not -1 and len(setDefines) is not 0:
		print "*** You set seed to %d but also set variables %s; you need to do one or the other ***\n" % (seed, setDefines)
		sys.exit()

	params = quantparse.ParseParams(chooseStrategy = strategy, preferenceForAuthorsVersion = preferenceForAuthorsVersion, setDefines = setDefines, doConfirm = doConfirm, discourseVarChance = discourseVarChance, onlyShow = onlyShow)

	if strategy == "pair":
		# TODO make this work with new output format.
		texts = []
		tries = 10
		seeds = []
		seed = chooser.nextSeed()
		for x in range(tries):
			seeds.append(seed)
			texts.append(collapseInputText(inputFiles, inputFileDir, params))
			seed = chooser.nextSeed()
		leastSimilarPair = differ.getTwoLeastSimilar(texts)
		text0 = texts[leastSimilarPair[0]]
		seed0 = seeds[leastSimilarPair[0]]
		text1 = texts[leastSimilarPair[1]]
		seed1 = seeds[leastSimilarPair[1]]
		render(outputFormat, text0, outputDir, outputFile, seed0, doFront, skipPadding, skipEndMatter, isDigital)
		render(outputFormat, text1, outputDir, alternateOutputFile, seed1, doFront, skipPadding, skipEndMatter, isDigital)

	else:
		copiesRequested = copies
		while copies >= 1:
			thisSeed = seed
			if strategy != "random" and strategy != "skipbanned":
				print "Ignoring seed (b/c strategy = %s)" % strategy
			elif randSeed:
				thisSeed = chooser.randomSeed()
				print "Seed (purely random): %d" % thisSeed
			elif seed is -1:
				thisSeed = chooser.nextSeed()
				print "Seed (next): %d" % thisSeed
			else:
				chooser.setSeed(thisSeed)
				print "Seed (requested): %d" % thisSeed

			collapsedText = collapseInputText(inputFiles, inputFileDir, params)
			collapsedFileName = outputDir + "collapsed.txt"

			fileio.writeOutputFile(collapsedFileName, collapsedText)

			thisOutputFile = outputFile
			if copiesRequested > 1:
				thisOutputFile = "%s-%s" % (outputFile, thisSeed)
			render(outputFormat, collapsedText, outputDir, thisOutputFile, thisSeed, doFront, skipPadding, skipEndMatter, isDigital)

			copies -= 1
			if copies > 0:
				print "%d cop%s left to generate." % (copies, "y" if copies is 1 else "ies")


def render(outputFormat, collapsedText, outputDir, outputFile, seed, doFront, skipPadding, skipEndMatter, isDigital):
	if outputFormat != "":
		renderParams = {
			"fileId": outputFile,
			"seed": seed,
			"doFront": doFront,
			"skipPadding": skipPadding,
			"skipEndMatter": skipEndMatter,
			"outputDir": outputDir,
			"isDigital": isDigital
		}
		renderer = None
		if outputFormat == "pdf":
			renderer = renderer_latex.RendererLatex(collapsedText, renderParams)
		elif outputFormat == "txt":
			renderer = renderer_text.RendererText(collapsedText, renderParams)
		elif outputFormat == "html":
			renderer = renderer_html.RendererHTML(collapsedText, renderParams)
		elif outputFormat == "md":
			renderer = renderer_markdown.RendererMarkdown(collapsedText, renderParams)
		elif outputFormat == "epub":
			renderer = renderer_epub.RendererEPub(collapsedText, renderParams)
		elif outputFormat == "mobi":
			renderer = renderer_mobi.RendererMobi(collapsedText, renderParams)
		elif outputFormat == "tweet":
			renderer = renderer_tweet.RendererTweet(collapsedText, renderParams)

		if renderer is None:
			print "No rendering requested or available."
		else:
			renderer.render()



def collapseInputText(inputFiles, inputFileDir, params):
	files = []
	fileList = []
	for iFile in inputFiles:
		result = readManifestOrFile(iFile, inputFileDir, params)
		files = files + result["files"]
		fileList = fileList + result["fileList"]

	fileTexts = []
	fileSetKey = hasher.hash(''.join(fileList))
	params.fileSetKey = fileSetKey
	for pos, file in enumerate(files):
		if len(params.onlyShow) == 0 or fileList[pos] in params.onlyShow or fileList[pos] == "globals.txt":
			print "Appending %s" % fileList[pos]
			fileTexts.append(file)
	joinedFileTexts = ''.join(fileTexts)
	collapsedText = collapse.go(joinedFileTexts, params)
	if collapsedText == "":
		sys.exit()

	return collapsedText

def readManifestOrFile(inputFile, inputFileDir, params):
	inputText = fileio.readInputFile(inputFileDir + inputFile)
	fileList = []
	files = []
	if inputText[:10] == "# MANIFEST":
		print "Reading manifest '%s'" % inputFile
		fileList = fileio.getFilesFromManifest(inputText)
		files = fileio.loadManifestFromFileList(inputFileDir, fileList)
	else:
		print "Reading file '%s'" % inputFile
		fileHeader = fileio.getFileId(inputFile)
		fileList = [inputFile]
		files = [fileHeader + inputText]
	return {
		"fileList": fileList,
		"files": files
	}




main()
