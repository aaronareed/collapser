
# Array of chunks. Each chunk is either text or a control sequence. A control sequence might have metadata and also a payload, which is an array of textons that each can have their own metadata. 



from quantlex import tokens
import chooser

chanceToUseAuthorsVersion = 25


# Create a class to store possible text alternatives we might print, and handle choosing an appropriate one.

class Alts:

	def __init__(self):
		self.alts = []
		self.authorPreferredPos = 0

	def add(self, txt):
		self.alts.append(txt)

	def setAuthorPreferred(self):
		self.authorPreferredPos = len(self.alts)

	def getAuthorPreferred(self):
		return self.alts[self.authorPreferredPos]

	def getRandom(self):
		return chooser.oneOf(self.alts)


# We have a series of tokens for a control sequence, everything between (and excluding) the square brackets. Each token has .type and .value.

def renderControlSequence(tokens, params):

	# Handle []
	if len(tokens) == 0:
		return ""

	alts = Alts()

	# [text] means a random chance of "text" or "", but if authorPreferred is true, never show it.
	if len(tokens) == 1 and tokens[0].type == "TEXT":
		alts.add("")
		if not params.useAuthorPreferred:
			alts.add(tokens[0].value)

	# [^text] means always show the text if authorPreferred is true.
	elif len(tokens) == 2 and tokens[0].type == "AUTHOR" and tokens[1].type == "TEXT":
		alts.add(tokens[1].value)
		if not params.useAuthorPreferred:
			alts.add("")

	# [~always print this]
	elif len(tokens) == 2 and tokens[0].type == "ALWAYS" and tokens[1].type == "TEXT":
		alts.add(tokens[1].value)

	else:
		# Iterate through each token. 
		index = 0
		lastText = ""
		while index < len(tokens):
			token = tokens[index]
			if token.type == "TEXT":
				lastText = token.value
			elif token.type == "DIVIDER":
				alts.add(lastText)
				lastText = ""
			elif token.type == "AUTHOR":
				alts.setAuthorPreferred()
			elif token.type == "ALWAYS":
				raise ValueError("The ALWAYS token can only be used with a single text, as in [~text]. In '%s'" % tokens)
			elif token.type == "NUMBER":
				alts.add("%d" % token.value)
			else:
				raise ValueError("Unhandled token %s: '%s'" % (token.type, token.value))
			index += 1

		# Handle being finished.
		if token.type == "TEXT":
			alts.add(lastText)
		elif token.type == "DIVIDER":
			alts.add("")

	if params.useAuthorPreferred or chooser.percent(chanceToUseAuthorsVersion):
		result = alts.getAuthorPreferred()
	else:
		result = alts.getRandom()
	return result



# The lexer should have guaranteed that we have a series of TEXT tokens interspersed with sequences of others nested between CTRLBEGIN and CTRLEND with no issues with nesting or incomplete tags.
def process(tokens, parseParams):
	output = []
	index = 0
	while index < len(tokens):
		token = tokens[index]
		rendered = ""
		if token.type == "TEXT":
			# print "Found TEXT: '%s'" % token.value
			rendered = token.value
		elif token.type == "CTRLBEGIN":
			# print "Found CTRLBEGIN: '%s'" % token.value
			ctrl_contents = []
			index += 1
			token = tokens[index]
			while token.type != "CTRLEND":
				# print ", %s: %s" % (token.type, token.value)
				ctrl_contents.append(token)
				index += 1
				token = tokens[index]
			rendered = renderControlSequence(ctrl_contents, parseParams)

		output.append(rendered)
		
		index += 1

	return output

class ParseParams:
	def __init__(self, useAuthorPreferred=False):
		self.useAuthorPreferred = useAuthorPreferred

# Call with an object of type ParseParams.
def parse(tokens, parseParams):
    # print "** PARSING **"
    renderedChunks = process(tokens, parseParams)
    finalString = ''.join(renderedChunks)
    return finalString
