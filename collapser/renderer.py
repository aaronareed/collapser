#!/usr/bin/python
# coding=utf-8

import quantparse
import ctrlseq
import macros
import variables
import chooser

import abc
import re


class RenderParams:

	def __init__(self, outputFormat = "", fileId = "", seed = -1, randSeed = False, doFront = False, skipPadding = False, endMatter = False, outputDir = "", isDigital = False, copies = 1, parseParams = None):
		self.outputFormat = outputFormat
		self.fileId = fileId
		self.seed = seed
		self.randSeed = randSeed
		self.doFront = doFront
		self.skipPadding = skipPadding
		self.endMatter = endMatter
		self.outputDir = outputDir
		self.isDigital = isDigital
		self.copies = copies
		self.renderer = None
		self.pdfPages = -1
		self.parseParams = parseParams



class Renderer(object):
	__metaclass__ = abc.ABCMeta

	def __init__(self, collapsedText, params):
		self.collapsedText = collapsedText
		self.params = params
		self.seqPos = 0
		self.prepareInputText()

	# Main entry point: takes a collapsed file and writes an output file in the given format.
	@abc.abstractmethod
	def render(self):
		pass

	# Part 1: takes the collapsed file and turns it into a valid input file for the desired output format (i.e., collapsed text to LaTeX, Markdown, etc.). Generally only called by render.
	@abc.abstractmethod
	def makeStagedFile(self):
		pass

	# Part 2: Takes the staged input file and creates the desired output format (i.e. LaTeX to PDF, Markdown to HTML, etc)
	@abc.abstractmethod
	def makeOutputFile(self):
		pass

	# Convert a formatting sequence like {i/italics} into the proper coding for this output format.
	@abc.abstractmethod
	def renderFormattingSequence(self, text):
		return text

	# Suggest an array of endMatters to append that won't exceed the page budget (if this format has one) based on stats stored from the last time we rendered; return an empty array if no suggestions.
	@abc.abstractmethod
	def suggestEndMatters(self):
		return []

	# Handle any text preparation that's agnostic across output formats.
	def prepareInputText(self):

		# Strip file identifiers (used by the lexer and parser to know what source file a given line comes from, so useful error messages can be printed).
		text = re.sub(r"\% file (.*)\n", "", self.collapsedText)

		self.collapsedText = text


	def renderFormattingSequences(self):
		# First swap in a render of an alternate scene if we need it, so the rest of the code will handle its formatting as per usual.
		if self.collapsedText.find("{alternate_scene}") >= 0:
			self.collapsedText = self.collapsedText.replace("{alternate_scene}", renderAlternateSequence(self.params.parseParams))

		self.resetFormattingSeqPos()
		fSeq = self.getNextFormatSeq()
		output = []
		while fSeq is not None:
			leadingText = fSeq[0]
			seqParams = fSeq[1:]
			rendered = self.renderFormattingSequence(seqParams)
			output.append(leadingText)
			output.append(rendered)
			fSeq = self.getNextFormatSeq()
		output.append(self.collapsedText[self.seqPos:])
		return ''.join(output)


	def resetFormattingSeqPos(self):
		self.seqPos = 0

	# Returns an array [contentSinceLast, parts] with all the content since the previous control sequence in position 0, and the parts of the control sequence found in subsequent positions.
	def getNextFormatSeq(self):
		startPos = self.collapsedText.find("{", self.seqPos)
		if startPos is -1:
			return None
		endPos = self.collapsedText.find("}", startPos)
		if endPos is -1:
			raise ValueError("Found { without closing brace.")
		codeSeq = self.collapsedText[startPos:endPos+1]
		contents = codeSeq[1:-1].split('/')
		contentSinceLast = self.collapsedText[self.seqPos:startPos]
		self.seqPos = endPos+1
		return [contentSinceLast] + contents




# Special code for the "Alternate Scene" End Matter.

def renderAlternateSequence(parseParams):
	result = getSequenceToRender(parseParams)
	sequencePicked = result[0]
	originChapter = result[1]
	setup = result[2]
	seq = quantparse.get_ctrlseq(sequencePicked)
	rendered = ctrlseq.render(seq, parseParams)
	rendered = "{i/(From Chapter %s...)} " % (originChapter) + setup + "\n\n" + rendered
	rendered = macros.expand(rendered, parseParams)
	return rendered

def getSequenceToRender(parseParams):
	# Pick a hand-tagged alternate scene based on which variables were set.
	choices = {}
	choices["Ch1IntroScene"] = ["Ch1IntroScene", 1, "Right from the start things were wrong, but I couldn’t see it. Maybe I didn’t want to. Or maybe I’m being too hard on myself. There wasn’t exactly a roadmap for what happened, a script to follow. But it’s undeniable that even on that very first night---the night of the Russian dance club, remember?---everything was already wrong."]
	choices["Ch3PartyConvo"] = ["Ch3PartyConvo", 3, "We listened to the music for a minute, surrounded by people who naturally knew how to Saturday night, without training. It was kind of nice being near them, at least."]
	choices["Ch4Interlude"] = ["Ch4Interlude", 4, "I worked up my courage and did a few of my own solo expeditions Downstairs, without telling him, but I couldn't convince myself to go very far. I hallucinated strange noises around corners: floorboards creaking, whispered sighs. I knew I was only scaring myself, but didn’t have it in me to stay down there for long."]
	choices["Ch6ResearchResults"] = ["Ch6ResearchResults", 6, "“I did some digging on your address,” she said, “and found something rather interesting.” She turned the last two words into an annoying sing-song. {i/Raaaaather intressting.} Trying to tune her out, I opened the file and pulled out the first page."]
	choices["Ch8SpiralHall"] = ["Ch8SpiralHall", 8, "It was subtle at first. But the horizontal hallways were becoming less and less level. We'd stumble on a floor that canted slightly left, or tilted a half-degree up or down. The walls, too, were growing angled, some leaning outward a degree or two instead of staying neatly parallel, or bent slightly inward at mismatched angles. It made us feel drunk. You've seen so many well-constructed hallways in your life, your brain doesn't know how to process ones that don't behave."]
	choices["Ch8HamsterWheel"] = ["Ch8HamsterWheel", 8, "Some of the rooms got larger, too big for rooms in a house. More like a school gymnasium. Still the same carpet, though. And it felt like we were seeing more of the anomalies, the farther in and deeper down we got. An explosion of pipes and plumbing, sticking out of a wall for no particular reason; weird cube-shaped extrusions or cavities in the edges of rooms. It was like the deeper we went, the more flexible the rules became—of architecture, of stability, of god knows what else."]
	choices["Ch8StageLadder"] = ["Ch8StageLadder", 8, "Some of the rooms got larger, too big for rooms in a house. More like a school gymnasium. Still the same carpet, though. And it felt like we were seeing more of the anomalies, the farther in and deeper down we got. An explosion of pipes and plumbing, sticking out of a wall for no particular reason; weird cube-shaped extrusions or cavities in the edges of rooms. It was like the deeper we went, the more flexible the rules became—of architecture, of stability, of god knows what else."]
	choices["Ch11TheBottom"] = ["Ch11TheBottom", 11, "He turned back to me again, no longer wistful but with dangerous sharpness. Maybe you've heard the phrase “thousand-yard stare” and maybe you've even seen one before, but I hadn't. It {i/struck} me. I believed everything he said next, no matter how fantastic. The words were only flavoring on the truth in that stare. {pp} “There's a room,” he began, voice graveling, “not much farther down from here. Different from anything up here. Bigger. A bit bigger.” That laugh again."]
	choices["Ch14Pathway"] = ["Ch14Pathway", 14, "I flailed, but my body was already past the edge of the door, my hands too slow to grab the frame, world tilting at a sickening angle. My sneaker tried desperately to glue itself to the carpet of the hall but my center of mass was too far out, way too far. My head dropped below my feet and I opened my mouth to scream as I began to fall into nothingness."]

# [DEFINE 50>@spiralhall|50>@nikofalls]
# [DEFINE 34>@noch8extra|33>@hamsterwheel|33>@stageladder]

	candidates = choices.keys()
	
	# Special cases and exceptions.
	if variables.check("bradphone"):
		# This is only an interesting choice if dadphone was set (the other version of the party conversation is much shorter).
		candidates.remove("Ch3PartyConvo")
	if variables.check("spiralhall"):
		candidates.remove("Ch8SpiralHall")
	if variables.check("hamsterwheel"):
		candidates.remove("Ch8HamsterWheel")
	if variables.check("stageladder"):
		candidates.remove("Ch8StageLadder")


	choice = chooser.oneOf(candidates)

	if choice == "Ch1IntroScene":
		variables.__v.shuffleGroupVal("clubintro")
	elif choice == "Ch3PartyConvo":
		variables.__v.shuffleGroupVal("dadphone")
	elif choice == "Ch4Interlude":
		variables.__v.shuffleGroupVal("cdrom")
	elif choice == "Ch6ResearchResults":
		variables.__v.shuffleGroupVal("vortex")
	elif choice == "Ch8SpiralHall":
		variables.set("spiralhall", True)
		variables.set("nikofalls", False)
	elif choice == "Ch8HamsterWheel":
		variables.set("hamsterwheel", True)
		variables.set("noch8extra", False)
		variables.set("stageladder", False)
	elif choice == "Ch8StageLadder":
		variables.set("stageladder", True)
		variables.set("noch8extra", False)
		variables.set("hamsterwheel", False)
	elif choice == "Ch11TheBottom":
		variables.__v.shuffleGroupVal("thecity")
	elif choice == "Ch14Pathway":
		variables.__v.shuffleGroupVal("ffchandelier")




	return choices[choice]





