
import chooser
import variables


# Create a class to store possible text alternatives we might print, and handle choosing an appropriate one.

class Alts:

	def __init__(self):
		self.alts = []
		self.authorPreferredPos = 0
		self.probabilityTotal = 0

	def add(self, txt, prob=None):
		self.alts.append(Item(txt, prob, False))
		if prob is not None:
			self.probabilityTotal += prob
			if self.probabilityTotal > 100:
				raise ValueError("Probabilities in ctrl sequence add up to %d which is > 100: '%s'" % (self.probabilityTotal, self))
		# print "Adding alt: list is now %s" % self

	def setAuthorPreferred(self):
		self.authorPreferredPos = len(self.alts)

	def getAuthorPreferred(self):
		return self.alts[self.authorPreferredPos].txt

	def getRandom(self):
		if self.probabilityTotal == 0:
			return chooser.oneOf(self.alts).txt
		else:
			return chooser.distributedPick(self.alts)

	def getLongest(self):
		longestPos = -1
		longestLength = -1
		for pos, alt in enumerate(self.alts):
			length = len(alt.txt)
			if length > longestLength:
				longestLength = length
				longestPos = pos
		return self.alts[longestPos].txt

	def __len__(self):
		return len(self.alts)

	def __str__(self):
		output = []
		for pos, item in enumerate(self.alts):
			ap = "^" if pos == self.authorPreferredPos else ""
			output.append("%s%s" % (ap, item))
		return str(output)

		# return str(list(map(lambda x: "%s%s" % ("^", x), self.alts)))

# Create a class for a single text item with probability.

class Item:
	def __init__(self, txt, prob, authorPreferred):
		self.txt = txt
		self.prob = prob
		self.authorPreferred = authorPreferred

	def __str__(self):
		base = "%s%s" % ("^" if self.authorPreferred else "", self.txt)
		if self.prob is not None:
			return "%s>%s" % (self.prob, base)
		return base


# We have a series of tokens for a control sequence, everything between (and excluding) the square brackets. Each token has .type and .value.

def render(tokens, params):

	# Handle []
	if len(tokens) == 0:
		return ""

	if tokens[0].type == "VARIABLE":
		return variables.render(tokens, params)

	alts = Alts()

	# [text] means a random chance of "text" or "", but if authorPreferred is true, never show it.
	if len(tokens) == 1 and tokens[0].type == "TEXT":
		alts.add("")
		if params.chooseStrategy != "author":
			alts.add(tokens[0].value)

	# [^text] means always show the text if authorPreferred is true.
	elif len(tokens) == 2 and tokens[0].type == "AUTHOR" and tokens[1].type == "TEXT":
		alts.add(tokens[1].value)
		if params.chooseStrategy != "author":
			alts.add("")

	# [~always print this]
	elif len(tokens) == 2 and tokens[0].type == "ALWAYS" and tokens[1].type == "TEXT":
		alts.add(tokens[1].value)

	else:
		# We have a series of alternates which we want to handle individually.
		index = 0
		numDividers = 0
		while index < len(tokens):

			thisAltBits = []

			endBit = False
			while not endBit and index < len(tokens):
				token = tokens[index]
				endBit = token.type == "DIVIDER"
				if not endBit:
					thisAltBits.append(token)
					index += 1

			item = parseItem(thisAltBits)
			if item.authorPreferred:
				alts.setAuthorPreferred()
			alts.add(item.txt, item.prob)

			index += 1

		if token.type == "DIVIDER":
			alts.add("")

	if params.chooseStrategy == "longest":
		return alts.getLongest()
	elif params.chooseStrategy == "author" or chooser.percent(params.preferenceForAuthorsVersion):
		result = alts.getAuthorPreferred()
	else:
		result = alts.getRandom()
	return result



		

# A chunk will be one alternative and metadata: "alpha", "80>alpha", "45>^", "". This is always in a context where we have multiple possibilities.
def parseItem(altBits):
	index = 0
	text = ""
	ap = False
	prob = None
	while index < len(altBits):
		token = altBits[index]
		if token.type in ("TEXT", "VARIABLE"):
			text = token.value
		elif token.type == "AUTHOR":
			ap = True
		elif token.type == "NUMBER":
			prob = token.value
		else:
			raise ValueError("Unhandled token %s: '%s'" % (token.type, token.value))		
		index += 1

	return Item(text, prob, ap)




