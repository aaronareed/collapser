# coding=utf-8

import renderer

import re
import result
import chooser
import fileio
import terminal
import sys

latexBegin = "fragments/begin.tex"
latexEnd = "fragments/end.tex"
latexFrontMatter = "fragments/frontmatter.tex"
latexPostFrontMatter = "fragments/postfrontmatter.tex"

PADDED_PAGES = 232


# TODO Add cleanup step to get rid of temp files

class RendererLatex(renderer.Renderer):

	def render(self):
		print "Rendering to LaTeX/PDF."
		self.makeStagedFile()
		self.makeOutputFile()

	def makeStagedFile(self):
		self.collapsedText = specialLatexAndPDFFixes(self.collapsedText)
		workFile = self.renderFormattingSequences()
		postLatexificationSanityCheck(workFile)
		stagedFileText = latexWrapper(workFile, self.params.seed, self.params.doFront)
		latexFileName = self.params.fileId + ".tex"
		fileio.writeOutputFile(self.params.outputDir + latexFileName, stagedFileText)

	def makeOutputFile(self):
		inputFileName = self.params.fileId + ".tex"
		outputFileName = self.params.fileId + ".pdf"
		outputPDF(self.params, inputFileName, outputFileName)

	def suggestEndMatters(self):
		global PADDED_PAGES
		suggestions = []
		print "In renderer_latex.suggestEndMatters, numPDFPages: %d" % self.params.pdfPages
		extraPages = PADDED_PAGES - self.params.pdfPages
		if self.params.isDigital:
			extraPages = 99

		endMatters = [
			["end-backers.txt", 3],
			["end-altscene.txt", 5],
			["end-stats.txt", 3],
			["end-abouttheauthor.txt", 3]
		]
		MAX_END_MATTERS = len(endMatters)

		while len(suggestions) < MAX_END_MATTERS:
			print "extraPages: %d" % extraPages
			endMatters = filter(lambda x: x[1] < extraPages, endMatters)
			print "%d endMatters left." % len(endMatters)
			if len(endMatters) == 0:
				break
			choicePos = chooser.number(len(endMatters)) - 1
			print "choicePos %d (%s)" % (choicePos, endMatters[choicePos][0])
			choice = endMatters[choicePos]
			suggestions.append(choice[0])
			extraPages -= choice[1]
			del endMatters[choicePos]

		return ["../fragments/backmatter.tex"] + suggestions

	def renderFormattingSequence(self, contents):
		code = contents[0]
		if code == "part":
			partNum = contents[1]
			partTitle = contents[2]
			# Hack to get "\mainmatter" to appear in right spot for opening chapter (otherwise page 1 is on the blank page preceeding and inner/outer positioning is wrong.)
			optMainMatter = ""
			if partNum == "PART ONE":
				optMainMatter = "\\mainmatter"
			return template_part[0] + optMainMatter + template_part[1] + partNum + template_part[2] + partTitle + template_part[3]
		if code == "epigraph":
			epigraph = contents[1]
			epigraph = fixLongEpigraphLines(epigraph)
			epigraph = fixMultiStanzaEpigraphs(epigraph)
			source = contents[2]
			return template_epigraph[0] + epigraph + template_epigraph[1] + source + template_epigraph[2]
		if code == "end_part_page":
			return template_end_part
		if code == "chapter":
			chapNum = contents[1]
			return template_chapter[0] + chapNum + template_chapter[1]
		if code == "endmatter":
			title = contents[1]
			return template_endmatter[0] + title + template_endmatter[1]
		if code == "section_break":
			return template_section_break
		if code == "verse":
			text = contents[1]
			return template_verse[0] + text + template_verse[1]
		if code == "verse_inline":
			text = contents[1]
			return template_verse_inline[0] + text + template_verse_inline[1]
		if code == "verse_inline_sc":
			text = contents[1]
			return template_verse_inline_sc[0] + text + template_verse_inline_sc[1]
		if code == "pp":
			return template_pp
		if code == "i":
			text = contents[1]
			return template_i[0] + text + template_i[1]
		if code == "sc":
			text = contents[1]
			return template_sc[0] + text + template_sc[1]
		if code == "scwide":
			text = contents[1]
			adjustedText = '\\kern.1em'.join(text)
			adjustedText = adjustedText.replace(" \\kern.1em", "\\kern.3em")
			return template_sc[0] + adjustedText + template_sc[1]
		if code == "vspace":
			text = contents[1]
			return template_vspace[0] + text + template_vspace[1]
		if code == "start_colophon":
			header = contents[1]
			return template_start_colophon[0] + header + template_start_colophon[1]
		if code == "finish_colophon":
			return template_finish_colophon
		if code == "url":
			url = contents[1]
			return template_url[0] + url + template_url[1]
		if code == "columns":
			numCols = contents[1]
			return template_columns[0] + numCols + template_columns[1]
		if code == "end_columns":
			return template_end_columns
		if code == "stars":
			return "\n \\vspace*{1\\nbs}\n \\scenestars\n"

		raise ValueError("Unrecognized command '%s' in control sequence '%s'" % (code, contents)) 



# Handle any tweaks to the rendered text before we begin the latex conversion.
def specialLatexAndPDFFixes(text):

	# Ensure verses don't break across pages.
	# {verse/A looking-glass held above this stream...}
	text = re.sub(r"{verse/(.*)}", r"{verse/\g<1> \\nowidow }", text)

	# Ensure no widows right before chapter breaks.
	text = re.sub(r"([\n\s]*){chapter/", r" \\nowidow \g<1>{chapter/", text)

	# Ensure no orphans right after section breaks.
	text = re.sub(r"{section_break}(\n*)(.*)\n", r"{section_break}\g<1>\g<2> \\noclub \n", text)

	# Use proper latex elipses
	text = re.sub(r"\.\.\. ", r"\ldots\ ", text)
	text = re.sub(r"… ", r"\ldots\ ", text)

	return text





# Raise errors if anything unexpected is found in the converted output.
def postLatexificationSanityCheck(text):
	# Look for unexpected characters etc. here
	# Note: can't use find_line_number_for_file etc. b/c those markers have been stripped.
	pos = text.find('_')
	if pos is not -1:
		raise ValueError("Found invalid underscore '_' character on line %d:\n%s" % (result.find_line_number(text, pos), result.find_line_text(text, pos)) )
	
	pos = text.find('''"''')
	if pos is not -1:
		raise ValueError("Found dumb quote character on line %d; use “ ” \n%s" % (result.find_line_number_for_file(text, pos), result.find_line_text(text, pos)) )

	return


# Wrap the converted latex in appropriate header/footers.
def latexWrapper(text, seed, includeFrontMatter):

	templates = {
		"begin": fileio.readInputFile(latexBegin),
		"end": fileio.readInputFile(latexEnd),
		"frontMatter": fileio.readInputFile(latexFrontMatter),
		"postFrontMatter": fileio.readInputFile(latexPostFrontMatter)
	}

	output = templates["begin"]
	if includeFrontMatter:
		output += templates["frontMatter"]
	output += templates["postFrontMatter"]
	output += text
	output += templates["end"]

	print "seed: %d" % seed
	if seed == -1:
		seedPrinted = "01893-b"
	elif seed < 9999:
		seedPrinted = "0%d" % seed
	else:
		seedPrinted = "%s" % seed

	# Insert the seed number where it appeared in front matter.
	msg = "This copy was generated from seed #%s and is the only copy generated from that seed." % seedPrinted
	if seed == -1:
		msg = "This run of Advance Reader Copies have all been generated from seed #%s." % seedPrinted
	output = output.replace("SEED_TEXT", msg)
	output = output.replace("SEED_NUMBER", "%s" % seedPrinted)

	frontMatterMsg = ""
	if seed == -1:
		frontMatterMsg = """This is a special Advance Reader Copy of \\textsc{Subcutanean}. In the final version, each printing of the book will be unique, generated from a specific seed. Words, sentences, or whole scenes may appear in this printing that do not appear in another. No two copies will be alike.

For now, each Advance Reader Copy in this printing shares the seed %s, and the same text.""" % seedPrinted
	else:
		frontMatterMsg = """The book you're holding is unique. There is no other exactly like it.

Each printing of \\textsc{Subcutanean} is different. This is the one and only version generated from seed %s. Words, sentences, or whole scenes may appear in some printings that do not appear in others. No two copies are alike.

But all of them are the same story, more or less. Don't worry about what's in the other versions. It doesn't matter. This is the one that's happening to you.

This is the one you have.""" % seedPrinted
	output = output.replace("FRONT_MATTER_MSG", "%s" % frontMatterMsg)

	# Special fix for half-space.
	output = output.replace("TROUBLEHALFSPACE", "trouble\\hspace{0.1em}s")

	return output

def outputPDF(params, inputFile, outputFile):
	global PADDED_PAGES
	result = terminal.runCommand('lualatex', '-interaction=nonstopmode -synctex=1 -recorder --output-directory="%s" "%s" ' % (params.outputDir, inputFile))
	# lualatex will fail (return exit code 1) even when successfully generating a PDF, so ignore result["success"] and just look at the output.
	latexLooksGood = postLatexSanityCheck(result["output"])
	if not latexLooksGood:
		print "*** Generation failed. Check .log file in output folder."
		sys.exit()

	stats = getStats(result["output"])
	numPages = stats["numPages"]
	print "Generated %d page PDF." % numPages
	params.pdfPages = numPages

	if not params.skipPadding:
		addPadding(params.outputDir, outputFile, stats["numPages"], PADDED_PAGES)
	if params.isDigital:
		print "isDigital, so adding cover"
		addCover(outputFile, "fragments/cover.pdf")


def postLatexSanityCheck(latexLog):
	numPages = 0

	overfulls = len(re.findall(r"\nOverfull \\hbox", latexLog))
	if overfulls > 500:
		print "Too many overfulls (found %d); halting." % overfulls
		return False

	result = getStats(latexLog)
	if result["numPages"] == -1:
		print "Couldn't find output line; halting."
		return False

	if result["numPages"] < 5 or result["numPages"] > 300:
		print "Unexpected page length (%d); halting." % result["numPages"]
		return False
	if result["numBytes"] < 80000 or result["numBytes"] > 3000000:
		print "Unexpected size (%d kb); halting." % (result["numBytes"] / 1000)
		return False

	# TODO: Check that it contains a key phrase that should exist in every version

	return True

def getStats(latexLog):
	data = { "numPages": -1, "numBytes": -1 }
	result = re.search(r"Output written on .*\.pdf \(([0-9]+) pages, ([0-9]+) bytes", latexLog)
	if result:
		data["numPages"] = int(result.groups()[0])
		data["numBytes"] = int(result.groups()[1])
	return data



def addPadding(outputDir, outputFile, reportedPages, desiredPageCount):

	print "Adding padding..."
	print "outputFile: '%s'" % outputFile
	outputFn = outputDir + outputFile
	numPDFPages = countPages(outputFn)
	if numPDFPages != reportedPages:
		print "*** Latex reported generating %d page PDF, but pdftk reported the output was %d pages instead. Aborting." % (reportedPages, numPDFPages)
		sys.exit()

	if numPDFPages > desiredPageCount:
		print "*** Generation exceeded maximum length of %d page: was %d pages." % (desiredPageCount, numPDFPages)
		sys.exit()

	# If equal, no action needed. Otherwise, add padding to the desired number of pages, which must remain constant in print on demand so the cover art doesn't need to be resized.

	if numPDFPages < desiredPageCount:
		tmpFn = outputDir + "padded-" + outputFile
		addBlankPages(outputFn, tmpFn, desiredPageCount - numPDFPages)
		terminal.rename(tmpFn, outputFn)
		numCombinedPages = countPages(outputFn)
		if numCombinedPages == desiredPageCount:
			print "Successfully padded to %d pages." % desiredPageCount
		else:
			print "*** Tried to pad output PDF to %d pages but result was %d pages instead." % (desiredPageCount, numPDFPages)
			sys.exit()


def addCover(inputPDF, coverfile):
	arguments = "A=%s B=output/%s cat A B output output/subcutanean-with-cover.pdf" % (coverfile, inputPDF)
	result = terminal.runCommand("pdftk", arguments)
	if not result["success"]:
		print "*** Couldn't generate PDF with cover. %s" % result["output"]
		sys.exit()


# Note: This requires pdftk, and specifically the version here updated for newer MacOS: https://stackoverflow.com/questions/39750883/pdftk-hanging-on-macos-sierra
# https://www.pdflabs.com/docs/pdftk-man-page/

def countPages(pdfPath):
	result = terminal.runCommand("pdftk", "%s dump_data | grep NumberOfPages" % pdfPath, shell=True)
	if not result["success"]:
		print "*** Couldn't get stats on output PDF; aborting."
		sys.exit()
	# == "NumberOfPages: 18"
	pagesResult = re.search(r"NumberOfPages: ([0-9]+)", result["output"])
	numPDFPages = int(pagesResult.groups()[0])
	return numPDFPages


# This also required pdftk, plus a blankpages.pdf with a large number of empty pages of the same size as the rest of the book.
def addBlankPages(inputPDF, outputPDF, numBlankPages):
	result = terminal.runCommand("pdftk", "A=%s B=extras/blankpages.pdf cat A B1-%s output %s" % (inputPDF, numBlankPages, outputPDF))
	if not result["success"]:
		print "*** Couldn't generate padded PDF. %s" % result["output"]
		sys.exit()


def fixLongEpigraphLines(txt):
	# This is a quick-and-dirty implementation that works for the couple of long poetry lines in Subcutanean's epigraphs, but wouldn't handle a lot of possible cases.
	lines = txt.split('\\')
	if len(lines) == 1:
		return txt
	output = []
	APPROX_MAX_LINE_LEN = 56
	AVG_WIDTH_LETTER = "r"
	for line in lines:
		if len(line.strip()) > APPROX_MAX_LINE_LEN:
			breakPos = line.rfind(" ", 0, APPROX_MAX_LINE_LEN)
			firstpart = line[:breakPos]
			output.append(firstpart)
			overflow = line[breakPos:]
			if len(overflow) > APPROX_MAX_LINE_LEN:
				print "*** Error: This epigraph line is just too damn long: '%s'" % line
				sys.exit()
			if overflow.strip() != "":
				invisibleText = AVG_WIDTH_LETTER * (APPROX_MAX_LINE_LEN - len(overflow))
				paddedOverflow = "\\phantom{%s} %s" % (invisibleText, overflow)
				output.append(paddedOverflow)
		elif line.strip() != "":
			output.append(line)
	result =  "\\\\".join(output)
	return result

def fixMultiStanzaEpigraphs(txt):
	return txt.replace("\\\\\n\n", """\\\\

\\noindent """)

template_chapter = ['''

\\clearpage 

\\begin{ChapterStart}
\\vspace*{2\\nbs} 
\\ChapterTitle{\\decoglyph{l8694} ''', ''' \\decoglyph{l11057}} 
\\end{ChapterStart}

''']

template_part = ['''

\\cleartorecto
\\thispagestyle{empty}
''', '''
\\begin{ChapterStart}
\\vspace*{4\\nbs} 
\\ChapterTitle{''', '''} 
\\vspace*{2\\nbs} 
\\ChapterTitle{''', '''} 
\\end{ChapterStart}

\\vspace*{4\\nbs}''']

template_endmatter = ['''

\\cleartorecto
\\thispagestyle{empty}
\\begin{ChapterStart}[6]
\\vspace*{1\\nbs} 
\\ChapterTitle{''', '''} 
\\end{ChapterStart}
\\vspace*{1\\nbs} 
''']

template_start_colophon = ['''

\\cleartorecto
\\thispagestyle{empty}
\\begin{parascale}[0.88]
\\vspace*{9\\nbs}
\\begin{adjustwidth}{4em}{4em}
\\begin{center}
\\textsc{''', '''}
\\end{center}
\\vspace*{2\\nbs}

''']

template_finish_colophon = '''

\\end{adjustwidth}
\\end{parascale}

'''

template_url = ['''
\\begin{center}
\\textsc{''', '''}
\\end{center}
''']

template_end_part = '''

\\cleartorecto

'''

template_epigraph = ['''
\\begin{adjustwidth}{3em}{3em}
\\begin{parascale}[0.88]
''', '''\\\\
\\par
\\noindent \\textit{''', '''}
\\end{parascale}
\\end{adjustwidth}
\\vspace*{2\\nbs} 
''']

template_section_break = '''

\\scenebreak

'''

template_pp = '''

'''

template_i = ['''\\textit{''', '''}''']
template_sc = ['''\\allsmcp{''', '''}''']

template_verse = ['''

\\vspace{1\\nbs}
\\begin{adjustwidth}{3em}{} 
\\textit{''', '''}
\\end{adjustwidth}
\\vspace{1\\nbs}

''']

template_verse_inline = ['''\\begin{adjustwidth}{3em}{} 
\\textit{''', '''}
\\end{adjustwidth}
\\noindent ''']

template_verse_inline_sc = ['''\\begin{adjustwidth}{3em}{} 
\\allsmcp{''', '''}
\\end{adjustwidth}
\\noindent ''']

template_vspace = ['''

\\vspace*{''', '''\\nbs}

'''] 

template_columns = ['''

\\begin{multicols}{''', '''}
\\begin{parascale}[0.8]

\\noindent ''']

template_end_columns = '''

\\end{parascale}
\\end{multicols}

'''

