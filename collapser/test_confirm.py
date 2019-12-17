# coding=utf-8

import variables
import quantlex
import quantparse
import ctrlseq
import confirm
import token_stream
import pytest

def parseResult(text, params = None):
	lexed = quantlex.lex(text)
	if not lexed.isValid:
		print lexed
		assert False
	if params == None:
		params = quantparse.ParseParams(chooseStrategy="random", doConfirm=False)
	params.originalText = text
	preppedTokens = quantparse.handleVariablesAndMacros(lexed.package, text, params)
	return preppedTokens

def getFirstCtrlSeq(tokens):
	ts = token_stream.SequenceStream(tokens)
	return ts.next() or []

def parseAndGetAlts(text):
	tokens = parseResult(text)
	ctrlcontents = getFirstCtrlSeq(tokens)
	return variables.renderAll(ctrlcontents[0])

def confirmRenderVariant(text, ctrlSeqPos, variantPos, trunc, maxWidth, prePostBuffer=850):
	tokens = parseResult(text)
	sequenceList = token_stream.SequenceStream(tokens)
	sequenceList.pos = ctrlSeqPos
	ctrlcontents = sequenceList.next()
	parseParams = quantparse.ParseParams()
	variants = ctrlseq.renderAll(ctrlcontents[0], parseParams, showAllVars=True)
	ctrlEndPos = ctrlcontents[1]
	ctrlStartPos = text.rfind("[", 0, ctrlEndPos)
	firstVariant = variants.alts[variantPos]
	return confirm.getContextualizedRenderedVariant(text, parseParams, ctrlStartPos, ctrlEndPos, sequenceList, firstVariant, prePostBuffer, trunc, trunc, maxWidth)



def test_renderAllVariables():
	text = "[DEFINE @alpha1]This is some text. [@alpha1>Variant the first|Version the second]. And some final text."
	alts = parseAndGetAlts(text)
	assert alts[0].txt == "Variant the first"
	assert alts[1].txt == "Version the second"

	text = "[DEFINE @beta]Text. [@beta>Only if beta.] End."
	alts = parseAndGetAlts(text)
	assert alts[0].txt == "Only if beta."
	assert alts[1].txt == ""

	text = "[DEFINE @gamma|@delta]Text. [@gamma>Gamma forever|@delta>This is delta|Or not] End."
	alts = parseAndGetAlts(text)
	assert alts[0].txt == "Gamma forever"
	assert alts[1].txt == "This is delta"
	assert alts[2].txt == "Or not"

def test_carets_multiline():
	text = """
So there were tapes where [this happened and I regretted so much all the things I'd said, the people I'd hurt,|the other thing took place despite all the best laid plans of mice and men to prevent it] and it was hard to watch."""
	rendered = confirmRenderVariant(text, 0, 0, "...", 70)
	assert rendered == """...
                          v
So there were tapes where this happened and I regretted so much all
the things I'd said, the people I'd hurt, and it was hard to watch....
                                        ^
"""

def test_carets_singleline():
	text = """
It was a very [wonderful|happy|great] day."""
	rendered = confirmRenderVariant(text, 0, 0, "...", 70)
	assert rendered == """...
It was a very wonderful day....
              ^       ^
"""

def test_carets_without_trunc():
	text = """
We're so [happy|sad] to see you."""
	rendered = confirmRenderVariant(text, 0, 0, "", 70)
	assert rendered == """
We're so happy to see you.
         ^   ^
"""

def test_without_leading_newlines():
	text = """
So I inserted a lot of stuff here because what I was most interested in was the situation where [this happened and I regretted so much all the things I'd said, the people I'd hurt,|the other thing took place despite all the best laid plans of mice and men to prevent it] and it was hard to watch without knowing the way the story was going to end."""
	rendered = confirmRenderVariant(text, 0, 0, "...", 80)
	assert rendered == """                                                               v
...cause what I was most interested in was the situation where this happened and
I regretted so much all the things I'd said, the people I'd hurt, and it was
                                                                ^
hard to watch without knowing the way the story ...
"""

def test_unicode():
	text = """
“Oh, shit.” Niko hadn’t found [the end of the hallway|my socks]. It had twisted a couple more times, he said,"""
	rendered = confirmRenderVariant(text, 0, 0, "", 70)
	assert rendered == """
                              v
"Oh, shit." Niko hadn't found the end of the hallway. It had twisted a
                                                   ^
couple more times, he said,
"""

def test_new_lines_after_variant():
	text = """
Although our story really did happen.

[Fine then. Here goes.|Okay, so. Here goes.|Fine. So.|Fine. Okay.] You ready?

This is what happened."""
	rendered = confirmRenderVariant(text, 0, 0, "", 70)
	assert rendered == """
Although our story really did happen.

v
Fine then. Here goes. You ready?
                    ^

This is what happened.
"""

def test_post_expansions_single_line():
	text = """
This is our story. Our [real|fake] story. [And how|Yep]. Great."""
	rendered = confirmRenderVariant(text, 0, 0, "", 70)
	assert rendered in ["""
This is our story. Our real story. And how. Great.
                       ^  ^
""", """
This is our story. Our real story. Yep. Great.
                       ^  ^
"""]

def test_post_expansions_multi_line():
	text = """
This is our story. Our [real|amazingly true] story. [And no one can ever tell us that we didn't really believe in what happened.|But it'll never be the same again after the things that occured to us, now will it bucko? No I absolutely don't think it will.]"""
	rendered = confirmRenderVariant(text, 0, 0, "", 70)
	assert rendered in ["""
                       v
This is our story. Our real story. And no one can ever tell us that we
                          ^
didn't really be
""", """
                       v
This is our story. Our real story. But it'll never be the same again
                          ^
after the things t
"""]


def test_pre_expansions_single_line():
	text = """
This is our story. Our [real|fake] story. [And how|Yep]. Great."""
	rendered = confirmRenderVariant(text, 1, 0, "", 70)
	assert rendered in ["""
This is our story. Our fake story. And how. Great.
                                   ^     ^
""", """
This is our story. Our real story. And how. Great.
                                   ^     ^
"""]

def test_pre_expansions_multi_line():
	text = """
This is our story. [And no one can ever tell us that we didn't really believe in what happened.|But it'll never be the same again after the things that occured to us, now will it bucko? No I absolutely don't think it will.] But it's our [amazing|real] story."""
	rendered = confirmRenderVariant(text, 1, 0, "", 80)
	assert rendered in ["""hat we didn't really believe in what happened. But it's our amazing story.
                                                            ^     ^
""", """it bucko? No I absolutely don't think it will. But it's our amazing story.
                                                            ^     ^
"""]

def test_macros_in_way():
	start = """connected to us via [exploded rays of chandelier|an exploded pathway of library]. """
	cruft = """[MACRO tube overview][@ffdropoff>a giant snake that had somehow coated itself in superglue and slithered through {tube overview end}|an immense pipe that had somehow coated itself in superglue and mugged {tube overview end}][MACRO tube overview end][~a secondhand furniture store, encrusting itself with beds, nightstands, dressers, floor lamps (some lit), bookshelves, bureaus, trashcans, and laundry hampers. Escher's own frat house.][MACRO set overview][~an experimental theater production set in an overstuffed and cramped bachelor pad bedroom, suspended in mid-air, furnishings cluttered together with no sensible order.]"""
	end = """Holy shit, I said. He laughed. Damn straight. Okay then. Who wants to go first?"""
	rendered = confirmRenderVariant(start + end, 0, 0, "", 70)
	expected = """                    v
connected to us via exploded rays of chandelier. Holy shit, I said. He
                                              ^
laughed. Damn straight. Okay then. W
"""
	assert rendered == expected

	rendered = confirmRenderVariant(start + cruft + end, 0, 0, "", 70)
	assert rendered == expected

def test_macro_removal_edge_cases():
	text = """some text [version a|version b]. [MACRO asdf ahksjdk asd fjhasfhksadfhkjadhskfahksjdfh ksadfhkas dfhkas dfhkas jdfhkas dfhjk asdhjfaks dfjh sd][~asdf]"""
	rendered = confirmRenderVariant(text, 0, 0, "", 80, 70)
	assert rendered == """some text version a.
          ^       ^
"""
	text = """some text [version a|version b]. [MACRO asdf][~ahksjdk asd fjhasfhksadfhkjadhskfahksjdfh ksadfhkas dfhkas dfhkas jdfhkas dfhjk asdhjfaks dfjh sd]"""
	rendered = confirmRenderVariant(text, 0, 0, "", 80, 70)
	assert rendered == """some text version a.
          ^       ^
"""

def test_defines_consistent():
	text = """[DEFINE @singulars|@plurals]when we found [@singulars>a block|some legos] and played with [@singulars>it|them]"""
	for i in range(10):
		rendered = confirmRenderVariant(text, 0, 0, "", 80, 70)
		assert rendered == """when we found a block and played with it
              ^     ^
"""
	for i in range(10):
		rendered = confirmRenderVariant(text, 0, 1, "", 80, 70)
		assert rendered == """when we found some legos and played with them
              ^        ^
"""

def test_defines_consistent():
	text = """[DEFINE @singulars|@plurals]when we found [@singulars>a block|some legos] under my bed, and played with {itthem}.[MACRO itthem][@singulars>it|@plurals>them]"""
	for i in range(10):
		rendered = confirmRenderVariant(text, 0, 0, "", 80, 70)
		assert rendered == """when we found a block under my bed, and played with it.
              ^     ^
"""

def test_stripMacros():
	text = """Hi![MACRO testmacro][This|or|that|or {another macro}][MACRO another macro][~Booya]Strip![MACRO blerg][@hello>yes|no]Again![MACRO final][thing|or|other thing]Bye!"""
	stripped = confirm.stripMacros(text)
	assert stripped == "Hi!Strip!Again!Bye!"
	text = """[MACRO testmacro][This|or|that]one[MACRO blerg][@hello>yes|no] [MACRO blob][~yes]two[MACRO final][thing|or|other thing]"""
	stripped = confirm.stripMacros(text)
	assert stripped == "one two"



def test_negated_defines_consistent():
	text = """[DEFINE @fftube|@ffset]I looked up and regretted it. [@fftube>Tube bit. {other sequence}|@ffset>Set part. {other sequence}][MACRO other sequence][~Other sequence.] [@fftube>|This only if ffset.]"""
	for i in range(10):
		rendered = confirmRenderVariant(text, 0, 0, "", 80, 80)
		assert rendered == """I looked up and regretted it. Tube bit. Other sequence.
                              ^                       ^
"""
	for i in range(10):
		rendered = confirmRenderVariant(text, 0, 1, "", 80, 80)
		assert rendered == """I looked up and regretted it. Set part. Other sequence. This only if ffset.
                              ^                       ^
"""		


def test_getCharsBefore():
	text = "This is 31 characters of text. Then some more comes here."
	assert confirm.getCharsBefore(text, 31, 1) == " "
	assert confirm.getCharsBefore(text, 31, 10) == " of text. "
	assert confirm.getCharsBefore(text, 31, 31) == "This is 31 characters of text. "
	assert confirm.getCharsBefore(text, 31, 300) == "This is 31 characters of text. "
	assert confirm.getCharsBefore(text, 1, 1) == "T"
	assert confirm.getCharsBefore(text, 1, 2) == "T"
	assert confirm.getCharsBefore(text, 0, 1) == ""
	assert confirm.getCharsBefore(text, 0, 2) == ""
	assert confirm.getCharsBefore(text, 56, 75) == "This is 31 characters of text. Then some more comes here"

def test_bad_getCharsBefore():
	text = "This is 31 characters of text. Then some more comes here."
	with pytest.raises(Exception) as e_info:
		confirm.getCharsBefore(text, 31, 0)
	with pytest.raises(Exception) as e_info:
		confirm.getCharsBefore(text, 31, -1)
	with pytest.raises(Exception) as e_info:
		confirm.getCharsBefore(text, -1, 1)
	assert confirm.getCharsBefore("012", 2, 1) == "1"
	with pytest.raises(Exception) as e_info:
		confirm.getCharsBefore("012", 3, 1)

def test_getCharsAfter():
	text = "This is 31 characters of text. Then some more comes here."
	assert confirm.getCharsAfter(text, 30, 1) == "T"
	assert confirm.getCharsAfter(text, 30, 10) == "Then some "
	assert confirm.getCharsAfter(text, 30, 26) == "Then some more comes here."
	assert confirm.getCharsAfter(text, 30, 300) == "Then some more comes here."
	assert confirm.getCharsAfter(text, 0, 300) == "his is 31 characters of text. Then some more comes here."
	assert confirm.getCharsAfter(text, 55, 1) == "."
	assert confirm.getCharsAfter(text, 55, 2) == "."
	assert confirm.getCharsAfter(text, 56, 1) == ""
	assert confirm.getCharsAfter(text, 56, 2) == ""

def test_bad_getCharsAfter():
	text = "This is 31 characters of text. Then some more comes here."
	with pytest.raises(Exception) as e_info:
		confirm.getCharsAfter(text, 31, 0)
	with pytest.raises(Exception) as e_info:
		confirm.getCharsAfter(text, 31, -1)
	with pytest.raises(Exception) as e_info:
		confirm.getCharsAfter(text, -1, 1)
	assert confirm.getCharsAfter("012", 1, 1) == "2"
	assert confirm.getCharsAfter("012", 2, 1) == ""
	with pytest.raises(Exception) as e_info:
		confirm.getCharsAfter("012", 3, 1)




def test_render_multiple_posts():
	text = "[DEFINE @test1|@test2][alpha|beta] and [@test1>gamma|delta] and [@test1>epsilon|zeta] and finally [@test1>upsilon|pi]."
	params = quantparse.ParseParams(setDefines=["test1"])
	tokens = parseResult(text, params)
	sequenceList = token_stream.SequenceStream(tokens)
	sequenceList.pos = 1
	rendered = confirm.getRenderedPost(text, params, 33, sequenceList)
	assert rendered == " and gamma and epsilon and finally upsilon."

def test_render_multiple_pres():
	text = "[DEFINE @test1|@test2]So: [@test1>gamma|delta] and [@test1>epsilon|zeta] and finally [@test1>upsilon|pi] [alpha|beta]"
	params = quantparse.ParseParams(setDefines=["test2"])
	tokens = parseResult(text, params)
	sequenceList = token_stream.SequenceStream(tokens)
	sequenceList.pos = 4
	rendered = confirm.getRenderedPre(text, params, 105, sequenceList)
	assert rendered == "So: delta and zeta and finally pi "

def test_trimming_partial_sequences():
	text = "ookieloos|25>@huskmen|25>@likenesses][MACRO double things][@lookieloos>Lookie-Loos|@huskmen>Husk-Men]So. "
	params = quantparse.ParseParams()
	result = confirm.cleanAndExpandBit(text, params, True, 90)
	assert result == "So. "

	text = "ookieloos|25>@huskmen|25>@likenesses][@huskmen>the husks|the likenesses]Ergo!"
	params = quantparse.ParseParams()
	result = confirm.cleanAndExpandBit(text, params, True, 90)
	assert result == "[@huskmen>the husks|the likenesses]Ergo!"

	text = "So, [MACRO double things][@lookieloos>Lookie-Loos|@huskmen>Husk-Men]then.[DEFINE 50>@lookieloos|25>@huskmen|25>@li"
	params = quantparse.ParseParams()
	result = confirm.cleanAndExpandBit(text, params, False, 105)
	assert result == "So, then."

def test_new_lines_after_expansion_dont_move_caret():
	pre = """inside and cold damp air spilled out; I could see something """
	variant1 = """glittering in the gloom behind him. Ice?"""
	post = """

Take a look, he said with a grin. I'll shine the light. But"""
	trunc = "..."
	maxLineLength = 80
	result = confirm.renderVariant(trunc, pre, variant1, post, trunc, maxLineLength, quantparse.ParseParams())
	assert result == """                                                               v
...inside and cold damp air spilled out; I could see something glittering in the
gloom behind him. Ice?
                     ^

Take a look, he said with a grin. I'll shine the light. But...
"""


# This test doesn't work because pytest somehow handles the unicode quote characters differently?
# def test_unicode_quotes_dont_mess_up_spacing():
# 	pre = """good.”

# He stared at me, hopeless. “There's no way back.”

# “"""
# 	variant1 = """There is. There has to be.” I took a breath. “We just have to"""
# 	variant2 = """No. Not yet.” I took a breath. “Not until we"""
# 	post = """ find it.”

# """
# 	trunc = "..."
# 	maxLineLength = 80
# 	result = confirm.renderVariant(trunc, pre, variant2, post, trunc, maxLineLength, quantparse.ParseParams())
# 	assert result == """...good."

# He stared at me, hopeless. "There's no way back."

#  v
# "No. Not yet." I took a breath. "Not until we find it."
#                                             ^

# ...
# """





