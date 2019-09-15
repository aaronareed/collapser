# coding=utf-8

import quantlex
import quantparse
import pytest

def parse(text, params = None):
	result = parseResult(text, params)
	if not result.isValid:
		print result
		assert False
	return result.package

def parseResult(text, params = None):
	lexed = quantlex.lex(text)
	if not lexed.isValid:
		print lexed
		assert False
	if params == None:
		params = quantparse.ParseParams(chooseStrategy="random", doConfirm=False)
	return quantparse.parse(lexed.package, text, params)



# When sent an array like ["A", "B", "C"] and a test to parse, will fail if after a large number of attempts to parse it hasn't seen each option appear as a parse result.
def verifyEachIsFound(opts, text):
	found = {}
	ctr = 0
	timesToTry = 100
	for key in opts:
		found[key] = False

	def anyNotFound():
		for key in found:
			if found[key] == False:
				return True
		return False

	while anyNotFound() and ctr < timesToTry:
		result = parse(text)
		for pos, key in enumerate(opts):
			if result == opts[pos]:
				found[key] = True
		if result not in opts:
			assert result == "Expected one of '%s'" % opts
		ctr += 1

	for key in found:
		if found[key] == False:
			assert "not found" == key


def test_alts():
	text = "We could be [heroes|villains]."
	options = ["We could be heroes.", "We could be villains."]
	for i in range(10):
		assert parse(text) in options
	text = "[a|b|c|d|e][1|2]"
	options = ["a1", "b1", "c1", "d1", "e1", "a2", "b2", "c2", "d2", "e2"]
	for i in range(10):
		assert parse(text) in options

def test_alt_spacing():
	text = "[a|aaa] [.|...]"
	options = ["a .", "a ...", "aaa .", "aaa ..."]
	for i in range(10):
		assert parse(text) in options

def test_all_alts():
	text = "[A|B|C]"
	verifyEachIsFound(["A", "B", "C"], text)
	
def test_empty_alts():
	text = "[A|B|]"
	verifyEachIsFound(["A", "B", ""], text)
	text = "[A||B]"
	verifyEachIsFound(["A", "B", ""], text)
	text = "[|A|B]"
	verifyEachIsFound(["A", "B", ""], text)

def test_empty_alts_in_situ():
	text = "Let's go[ already]."
	options = ["Let's go already.", "Let's go."]
	for i in range(10):
		assert parse(text) in options

	text = "She was [rather |]charming."
	options = ["She was charming.", "She was rather charming."]
	for i in range(10):
		assert parse(text) in options

def test_single_texts():
	text = "alpha [beta ]gamma"
	verifyEachIsFound(["alpha beta gamma", "alpha gamma"], text)

def test_author_preferred():
	text = "[A|B|C]"
	params = quantparse.ParseParams(chooseStrategy="author")
	for i in range(10):
		assert parse(text, params) == "A"

	text = "[^A|B|C]"
	for i in range(10):
		assert parse(text, params) == "A"

	text = "[A|B|^C|D]"
	for i in range(10):
		assert parse(text, params) == "C"

	text = "[A|^Z]"
	for i in range(10):
		assert parse(text, params) == "Z"

	text = "[A|^|C|D|E|F|G|H|I|J|K]"
	for i in range(10):
		assert parse(text, params) == ""

	text = "The author prefers no [|flowery |disgusting ]adjectives."
	for i in range(10):
		assert parse(text, params) == "The author prefers no adjectives."

def test_author_preferred_single():
	text = "A[^B]C"
	params = quantparse.ParseParams(chooseStrategy="author")
	for i in range(10):
		assert parse(text, params) == "ABC"
	text = "A[B]C"
	for i in range(10):
		assert parse(text, params) == "AC"

def test_empty_with_author_pref():
	text = "[50> as mine|^]"
	verifyEachIsFound([" as mine", ""], text)
	params = quantparse.ParseParams(chooseStrategy="author")
	for i in range(10):
		assert parse(text, params) == ""

def test_always():
	text = "[~alpha]"
	for i in range(10):
		assert parse(text) == "alpha"

def test_always_is_exclusive():
	text = "[~alpha|beta]"
	with pytest.raises(Exception) as e_info:
		parse(text)

def test_number_values_cant_exceed_100():
	text = "[50>alpha|50>omega]"
	assert parse(text) in ["alpha", "omega"]
	text = "[50>alpha|51>omega]"
	res = parseResult(text)
	assert res.isValid == False
	text = "[50>alpha|50>omega|50>omega|50>omega|50>omega]"
	res = parseResult(text)
	assert res.isValid == False

def test_can_use_author_preferred_with_prob():
	text = "[80>alpha|10>beta|10>^gamma]"
	assert parse(text) in ["alpha", "beta", "gamma"]
	params = quantparse.ParseParams(chooseStrategy="author")
	for i in range(10):
		assert parse(text, params) == "gamma"

def test_can_use_blanks_with_prob():
	text = "[60>|40>pizza]"
	verifyEachIsFound(["", "pizza"], text)
	text = "[65>pizza|35>]"
	verifyEachIsFound(["", "pizza"], text)

def test_probability_works():
	text = "[90>alpha|10>beta]"
	timesA = 0
	timesB = 0
	for _ in range(100):
		result = parse(text)
		if result == "alpha":
			timesA += 1
		if result == "beta":
			timesB += 1
	assert timesA > timesB

	text = "[10>alpha|90>beta]"
	timesA = 0
	timesB = 0
	for _ in range(100):
		result = parse(text)
		if result == "alpha":
			timesA += 1
		if result == "beta":
			timesB += 1
	assert timesB > timesA

def test_less_than_100_is_chance_of_blank():
	text = "[25>alpha|35>beta]"
	verifyEachIsFound(["alpha", "beta", ""], text)

def test_defines_are_stripped():
	text = "[DEFINE @test1][DEFINE @test2]This is a test of [DEFINE @test3]stripping.[DEFINE   @test4]"
	assert parse(text) == "This is a test of stripping."

def test_simple_defines_set_randomly():
	text = "[DEFINE @test]"
	foundY = False
	foundN = False
	ctr = 0
	while ((not foundY) or (not foundN)) and ctr < 100:
		result = parse(text)
		if quantparse.variables.check("test") == True:
			foundY = True
		elif quantparse.variables.check("test") == False:
			foundN = True
		ctr += 1
	assert foundY
	assert foundN

def test_simple_define_with_author_preferred():
	text = "[DEFINE ^@test]"
	params = quantparse.ParseParams(chooseStrategy="author")
	for _ in range(100):
		parse(text, params)
		assert quantparse.variables.check("test") == True
	text = "[DEFINE @test]"
	for _ in range(100):
		parse(text, params)
		assert quantparse.variables.check("test") == False
	text = "[DEFINE ^@test1][DEFINE @test2]"
	for _ in range(10):
		parse(text, params)
		assert quantparse.variables.check("test1") == True	
		assert quantparse.variables.check("test2") == False	


def test_defines_with_probabilities():
	text = "A [DEFINE 80>@beta|20>^@barcelona] C"
	params = quantparse.ParseParams(chooseStrategy="author")
	for _ in range(100):
		output = parse(text, params)
		assert quantparse.variables.check("barcelona") == True

def test_defines_with_probabilities_must_sum_to_100():
	text = "[DEFINE 80>@A|19>@B]"
	with pytest.raises(Exception) as e_info:
		parse(text)
	text = "[DEFINE 80>@A|21>@B]"
	with pytest.raises(Exception) as e_info:
		parse(text)

	text = "[DEFINE 99>@A]"
	with pytest.raises(Exception) as e_info:
		parse(text)
	text = "[DEFINE 1>@A]"
	with pytest.raises(Exception) as e_info:
		parse(text)

	text = "[DEFINE 10>@A|15>@B|4>@C|31>@D|38>@E|2>@F]"
	assert parse(text) == ""
	text = "[DEFINE 10>@A|15>@B|31>@D|38>@E|2>@F]"
	with pytest.raises(Exception) as e_info:
		parse(text)

def test_equal_distribution_defines():
	text = "[DEFINE @wordy|@average|@taciturn]I am a [@wordy>rather wordy|@average>normal|@taciturn>quiet] person."
	verifyEachIsFound(["I am a rather wordy person.", "I am a normal person.", "I am a quiet person."], text)

def test_multiple_defines_is_bad():
	text = "[DEFINE @alpha] Some text. [@alpha>Yes.] Some more. [DEFINE 80>@beta|20>@alpha]. Some final text."
	with pytest.raises(Exception) as e_info:
		parse(text)
	text = "[DEFINE 25>@alpha|75>^@alpha]."
	with pytest.raises(Exception) as e_info:
		parse(text)

def test_okay_to_define_after_using():
	text = "[@test>Test test.] Then stuff. [DEFINE ^@test]"
	params = quantparse.ParseParams(chooseStrategy="author")
	assert parse(text, params) == "Test test. Then stuff. "

def test_vars_collected_and_stripped():
	text = "[DEFINE @alpha][DEFINE 50>@beta|50>@gamma]Hello, friends![DEFINE @omega]"
	result = parse(text)
	keys = quantparse.variables.showVars()
	assert len(keys) == 4
	assert "alpha" in keys
	assert "beta" in keys
	assert "gamma" in keys
	assert "omega" in keys
	assert result == "Hello, friends!"
	assert quantparse.variables.check("random") == False

def test_variable_refs():
	text = "[DEFINE ^@test][@test>This is a test message. ]Huzzah!"
	params = quantparse.ParseParams(chooseStrategy="author")
	result = parse(text, params)
	assert result == "This is a test message. Huzzah!"
	text = "[DEFINE @test][@test>This is a test message. ]Huzzah!"
	result = parse(text, params)
	assert result == "Huzzah!"

def test_parse_variable_with_else():
	text = "A [DEFINE @test][@test>if text|else text] C"
	params = quantparse.ParseParams(chooseStrategy="author")
	result = parse(text, params)
	assert result == "A else text C"
	text = "A [DEFINE ^@test][@test>if text|else text] C"
	result = parse(text, params)
	assert result == "A if text C"

def test_parse_variable_with_backward_else():
	text = "A[DEFINE ^@test][@test>| else text only ]C"
	params = quantparse.ParseParams(chooseStrategy="author")
	result = parse(text, params)
	assert result == "AC"
	text = "A[DEFINE @test][@test>| else text only ]C"
	result = parse(text, params)
	assert result == "A else text only C"

def test_variable_with_named_options():
	text = "[DEFINE 25>@alpha|25>@beta|25>@gamma|25>@epsilon][@alpha>Adam|@beta>Barney|@gamma>Gerald|@epsilon>Ernie]"
	result = parse(text)
	assert result in ["Adam", "Barney", "Gerald", "Ernie"]

def test_if_some_named_only_last_unnamed():
	text = "[DEFINE 50>@alpha|50>@beta][Barney|@alpha>Arnold]"
	result = parseResult(text)
	assert result.isValid == False
	text = "[DEFINE 33>@alpha|33>@beta|34>@gamma][@alpha>Andrew|Bailey|@gamma>Gary]"
	with pytest.raises(Exception) as e_info:
		parse(text)

def test_named_options_all_in_same_ctrl_group():
	text = "[DEFINE 25>@alpha|25>@beta|25>@gamma|25>@epsilon][DEFINE 50>@larry|25>@moe|25>@curly][@alpha>Adam|@beta>Barney|@larry>Gerald|@epsilon>Ernie]"
	with pytest.raises(Exception) as e_info:
		parse(text)

def test_macro_defs_are_recognized_and_stripped():
	text = "[MACRO test macro][~always show this]"
	result = parse(text)
	assert result == ""
	assert quantparse.macros.isMacro("test macro") == True
	assert quantparse.macros.isMacro("nonsense") == False

def test_invalid_macro_def():
	text = "[MACRO test] A macro always must be followed by a CtrlSeq"
	with pytest.raises(Exception) as e_info:
		parse(text)
	text = "[MACRO test][20>always|50>never] doubly defined [MACRO test][~whatever]"
	with pytest.raises(Exception) as e_info:
		parse(text)

def test_macro_expansion():
	text = '''[MACRO test][~always show this]Hello, and {test}'''
	result = parse(text)
	assert result == "Hello, and always show this"	
	text = '''Thank you, and {bye bye}.[MACRO bye bye][~goodnight]'''
	result = parse(text)
	assert result == "Thank you, and goodnight."	
	text = '''{night}, and dream.[MACRO night][~Night]'''
	result = parse(text)
	assert result == "Night, and dream."	

# Now we want to leave these to go forward to latexifier.
# def test_macro_never_defined():
# 	text = '''Thank you, and {goodnight}'''
# 	with pytest.raises(Exception) as e_info:
# 		parse(text)
# 	text = '''[MACRO goodnigh][~A]Thank you, and {goodnight}'''
# 	with pytest.raises(Exception) as e_info:
# 		parse(text)

def test_macro_bad():
	text = '''Thank you {} and whatever.'''
	with pytest.raises(Exception) as e_info:
		parse(text)

def test_macro_expansions():
	text = '''[MACRO options][alpha|beta|gamma|]{options}'''
	verifyEachIsFound(["alpha", "beta", "gamma", ""], text)
	text = '''[MACRO a1][A|B][MACRO a2][C|D]{a1}{a2}'''
	verifyEachIsFound(["AC", "AD", "BC", "BD"], text)
	text = '''[MACRO a1][50>alpha|25>cappa]{a1}'''
	verifyEachIsFound(["alpha", "cappa", ""], text)


def test_nested_macros():
	text = '''[DEFINE ^@alpha][@alpha>{mactest}][MACRO mactest][~beta]'''
	params = quantparse.ParseParams(chooseStrategy="author")
	result = parse(text, params)
	assert result == "beta"
	text = '''[MACRO firstname][^Aaron|Bob|Carly][MACRO lastname][^Alda|Brockovich|Clayton]{firstname} {lastname}, {firstname} {lastname}'''
	result = parse(text, params)
	assert result == "Aaron Alda, Aaron Alda"

def test_more_nested_macros():
	text = '''[MACRO alpha][~apple {beta}][MACRO beta][~bear {cappa}][MACRO cappa][@delta>dog][DEFINE ^@delta]{alpha}'''
	params = quantparse.ParseParams(chooseStrategy="author")
	result = parse(text, params)
	assert result == "apple bear dog"
	text = '''{alpha}[MACRO alpha][~apple {beta}][MACRO beta][~bear {cappa}][MACRO cappa][@delta>dog][DEFINE ^@delta]'''
	result = parse(text, params)
	assert result == "apple bear dog"
	text = '''[MACRO alpha][~apple {beta}]{alpha}[MACRO beta][~bear {cappa}][MACRO cappa][@delta>dog][DEFINE ^@delta]'''
	result = parse(text, params)
	assert result == "apple bear dog"

def test_layered_macros():
	text = '''[MACRO alpha][@zetta>Use {beta} macro.][MACRO beta][@yotta>this is yotta|not yotta][DEFINE ^@zetta][DEFINE @yotta]{alpha}'''
	params = quantparse.ParseParams(chooseStrategy="author")
	result = parse(text, params)
	assert result == "Use not yotta macro."

	# Expanding macros should work even if start pos stays the same each time for a few expansions.
	text = '''{alpha}[MACRO alpha][~{beta}][MACRO beta][~{gamma}][MACRO gamma][~asdf]'''
	result = parse(text)
	assert result == "asdf"

def test_recursive_macro_guard():
	text = '''{alpha}[MACRO alpha][~{alpha}]'''
	with pytest.raises(Exception) as e_info:
		result = parse(text)

	text = '''{alpha}[MACRO alpha][~{beta}][MACRO beta][~{gamma}][MACRO gamma][~{alpha}]'''
	with pytest.raises(Exception) as e_info:
		result = parse(text)


def test_sticky_macro():
	text = '''[MACRO Soda][25>Sprite|25>Pepsi|25>Coke|25>Fresca]{Soda} {Soda} {Soda} {Soda} {Soda} {Soda} {Soda} {Soda} {Soda} {Soda}'''
	params = quantparse.ParseParams(chooseStrategy="random")
	result = parse(text, params).split()
	assert result[0] != result[1] or result[1] != result[2] or result[2] != result[3] or result[3] != result[4] or result[4] != result[5] or result[5] != result[6] or result[6] != result[7] or result[7] != result[8] or result[8] != result[9]
	text = '''[STICKY_MACRO Soda][25>Sprite|25>Pepsi|25>Coke|25>Fresca]{Soda} {Soda} {Soda} {Soda} {Soda} {Soda} {Soda} {Soda} {Soda} {Soda}'''
	result = parse(text, params).split()
	assert result[0] == result[1] and result[1] == result[2] and result[2] == result[3] and result[3] == result[4] and result[4] == result[5] and result[5] == result[6] and result[6] == result[7] and result[7] == result[8] and result[8] == result[9]

def test_alt_choose_strategies():
	text = '''[A|B|The longest possible option] is [A|definitely absolutely the longest|pretty long] and [this is the longest for sure|also pretty long, really|not so long].'''
	params = quantparse.ParseParams(chooseStrategy="longest")
	for i in range(10):
		assert parse(text, params) == "The longest possible option is definitely absolutely the longest and this is the longest for sure."

def test_set_defines():
	text = '''[DEFINE @alpha][@alpha>This is A text. |This is null. ][DEFINE 34>@gamma|33>@omega|33>@delta][@omega>This is O text. ][@delta>This is D text. ]'''
	params = quantparse.ParseParams(setDefines=["alpha", "omega"])
	for i in range(10):
		assert parse(text, params) == "This is A text. This is O text. "
	params = quantparse.ParseParams(setDefines=["delta"])
	for i in range(10):
		assert parse(text, params) in ["This is A text. This is D text. ", "This is null. This is D text. "]

def test_negated_set_defines():
	text = '''[DEFINE @alpha][@alpha>This is A text. |This is null. ][DEFINE 34>@gamma|33>@omega|33>@delta][@omega>This is O text. ][@delta>This is D text. ]'''
	params = quantparse.ParseParams(setDefines=["!alpha", "!omega", "delta"])
	for i in range(10):
		assert parse(text, params) == "This is null. This is D text. "

def test_longest():
	text = '''This is [so very super long|short] and that is [quick|such a laborious process].'''
	params = quantparse.ParseParams(chooseStrategy="longest")
	for i in range(10):
		assert parse(text, params) == "This is so very super long and that is such a laborious process."
	params = quantparse.ParseParams(chooseStrategy="shortest")
	for i in range(10):
		assert parse(text, params) == "This is short and that is quick."


def test_longest_bool_defines():
	text = '''[DEFINE @alpha][DEFINE @beta]This is [@alpha>quite long|short] and this is [@beta>extremely long|small].'''
	params = quantparse.ParseParams(chooseStrategy="longest")
	for i in range(10):
		assert parse(text, params) == "This is quite long and this is extremely long."
	params = quantparse.ParseParams(chooseStrategy="shortest")
	for i in range(10):
		assert parse(text, params) == "This is short and this is small."

def test_longest_enum_defines():
	text = '''[DEFINE 50>@alpha|50>@beta][DEFINE 33>@A|33>@B|34>@C]This is [@alpha>quite a long thing to say][@beta>not much], and that is [@A>succinct][@B>rather long-winded if you ask me].'''
	params = quantparse.ParseParams(chooseStrategy="longest")
	for i in range(10):
		assert parse(text, params) == "This is quite a long thing to say, and that is rather long-winded if you ask me."
	params = quantparse.ParseParams(chooseStrategy="shortest")
	for i in range(10):
		assert parse(text, params) == "This is not much, and that is ."

def test_zeros_never_appear():
	text = '''Alpha [0>never print this ]beta.'''
	for i in range(1000):
		assert parse(text) == "Alpha beta."
	text = '''Alpha [50>acceptable |50>also acceptable |0>never okay ]beta.'''
	for i in range(1000):
		assert parse(text) != "Alpha never okay beta."




def test_long_passages():
	text = '''

# Pick one of two significant moments: either a spiral hallway that one of them doesn't see, or Niko almost falling and Ryan having to talk him to safety.

[DEFINE 50>@spiralhall|50>@nikofalls]

# Optionally include an extra sequence exploring a weird example of architecture.

[DEFINE 34>@noch8extra|33>@hamsterwheel|33>@stageladder]

“So it's progress, right?” Niko was saying. We were in the [funny|oddly]-shaped room behind the closet [@spiralhall>with the spiral hall ][@hamsterwheel>and a hamster wheel ]and {stuff was cool}.

[MACRO stuff was cool][stuff was real cool|it was okay|I guess stuff was nice]
'''
	params = quantparse.ParseParams(chooseStrategy="author")
	result = parse(text, params)
	expected = '''







“So it's progress, right?” Niko was saying. We were in the funny-shaped room behind the closet with the spiral hall and stuff was real cool.


'''
	assert result == expected

	text = '''grappling hooks [we found at|from] the sporting goods store. The box called them “{Grapples},” which seemed incongruously cheerful.

[STICKY_MACRO Grapples][Grapple Buddies|Grip Monkeys]

[DEFINE ^@canyons]
[@canyons>Niko took me up into the canyons to teach me some climbing and test the {Grapples}. It felt strange to leave the house, breathe hot air and smell external things, outside things, moss and leaves and rain. Climbing didn't come naturally to me but Niko was patient and a good teacher, and knew his knots and technique. By the time we were loading our packs for the next expedition, I felt reasonably confident I wouldn't immediately kill us both.]'''
	params = quantparse.ParseParams(chooseStrategy="author")
	result = parse(text, params)
	expected = '''grappling hooks we found at the sporting goods store. The box called them “Grapple Buddies,” which seemed incongruously cheerful.




Niko took me up into the canyons to teach me some climbing and test the Grapple Buddies. It felt strange to leave the house, breathe hot air and smell external things, outside things, moss and leaves and rain. Climbing didn't come naturally to me but Niko was patient and a good teacher, and knew his knots and technique. By the time we were loading our packs for the next expedition, I felt reasonably confident I wouldn't immediately kill us both.'''
	assert result == expected





	