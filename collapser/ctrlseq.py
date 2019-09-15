
import chooser
import variables
import result

# Create a class to store possible text alternatives we might print, and handle choosing an appropriate one.

class Alts:

	def __init__(self):
		self.alts = []
		self.authorPreferredPos = 0
		self.probabilityTotal = 0

	def add(self, txt, prob=None):
		if prob == 0:
			return
		self.alts.append(Item(txt, prob, False))
		if prob is not None:
			self.probabilityTotal += prob
			if self.probabilityTotal > 100:
				badResult = result.Result(result.PARSE_RESULT)
				badResult.flagBad("Probabilities in ctrl sequence add up to %d which is > 100" % self.probabilityTotal, str(self), 0)
				raise result.ParseException(badResult)

	def setAuthorPreferred(self):
		self.authorPreferredPos = len(self.alts)

	def getAuthorPreferred(self):
		return self.alts[self.authorPreferredPos].txt

	def getRandom(self):
		if self.probabilityTotal == 0:
			return chooser.oneOf(self.alts).txt
		else:
			return chooser.distributedPick(self.alts)

	def getSortedAlts(self):
		return sorted(self.alts, key = lambda a: len(a.txt))

	def getLongest(self):
		lastPos = len(self.alts)-1
		return self.getSortedAlts()[lastPos].txt

	def getShortest(self):
		return self.getSortedAlts()[0].txt

	def __len__(self):
		return len(self.alts)

	def __str__(self):
		output = []
		for pos, item in enumerate(self.alts):
			ap = "^" if pos == self.authorPreferredPos else ""
			output.append("%s%s" % (ap, item))
		return str(output)


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


def renderAll(tokens, params, showAllVars=False):

	alts = Alts()

	# Handle []
	if len(tokens) == 0:
		return alts

	if tokens[0].type == "VARIABLE":
		if showAllVars:
			alts.alts.extend(variables.renderAll(tokens))
		else:
			alts.add(variables.render(tokens, params))

	# [text] means a random chance of "text" or "", but if authorPreferred is true, never show it.
	elif len(tokens) == 1 and tokens[0].type == "TEXT":
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

			item = parseItem(thisAltBits, variablesAllowed=False)
			if item.authorPreferred:
				alts.setAuthorPreferred()
			alts.add(item.txt, item.prob)

			index += 1

		if token.type == "DIVIDER":
			alts.add("")

	return alts

# We have a series of tokens for a control sequence, everything between (and excluding) the square brackets. Each token has .type and .value.

def render(tokens, params):

	alts = renderAll(tokens, params)
	if len(alts) == 0:
		return ""

	if params.chooseStrategy == "longest":
		return alts.getLongest()
	elif params.chooseStrategy == "shortest":
		return alts.getShortest()
	elif params.chooseStrategy == "author" or chooser.percent(params.preferenceForAuthorsVersion):
		result = alts.getAuthorPreferred()
	else:
		result = alts.getRandom()

	return result



		

# A chunk will be one alternative and metadata: "alpha", "80>alpha", "45>^", "". This is always in a context where we have multiple possibilities.
def parseItem(altBits, variablesAllowed=True):
	index = 0
	text = ""
	ap = False
	prob = None
	while index < len(altBits):
		token = altBits[index]
		if variablesAllowed == False and token.type == "VARIABLE":
			badResult = result.Result(result.PARSE_RESULT)
			badResult.flagBad("Found unexpected variable '%s'" % token.value, str(altBits), 0)
			raise result.ParseException(badResult)
		if token.type in ("TEXT", "VARIABLE"):
			text = token.value
		elif token.type == "AUTHOR":
			ap = True
		elif token.type == "NUMBER":
			prob = token.value
		else:
			badResult = result.Result(result.PARSE_RESULT)
			badResult.flagBad("Unhandled token %s: '%s'" % (token.type, token.value), str(altBits), 0)
			raise result.ParseException(badResult)
		index += 1

	return Item(text, prob, ap)




