import re
from refo import finditer, Predicate, Star, Any
import jieba.posseg as pseg
from jieba import suggest_freq
from SPARQLWrapper import SPARQLWrapper, JSON


sparql_base = SPARQLWrapper("http://localhost:3030/openkgDemo/query")

# SPARQL config
SPARQL_PREAMBLE = """
PREFIX cns:<http://cnschema.org/>
PREFIX cns_people:<http://cnschema.org/Person/>
PREFIX cns_place:<http://cnschema.org/Place/>
"""

SPARQL_TEM = "{preamble}\n" + \
             "SELECT DISTINCT {select} WHERE {{\n" + \
             "{expression}\n" + \
             "}}\n"

INDENT = "    "


class Word(object):
    """treated words as objects"""
    def __init__(self, token, pos):
        self.token = token
        self.pos = pos


class W(Predicate):
    """object-oriented regex for words"""
    def __init__(self, token=".*", pos=".*"):
        self.token = re.compile(token + "$")
        self.pos = re.compile(pos + "$")
        super(W, self).__init__(self.match)

    def match(self, word):
        m1 = self.token.match(word.token)
        m2 = self.pos.match(word.pos)
        return m1 and m2


class Rule(object):
    def __init__(self, condition=None, action=None):
        assert condition and action
        self.condition = condition
        self.action = action

    def apply(self, sentence):
        matches = []
        for m in finditer(self.condition, sentence):
            i, j = m.span()
            print(i, j)
            matches.extend(sentence[i:j])
        if __name__ == '__main__':
            print("----------applying %s----------" % self.action.__name__)
        return self.action(matches)


def who_is_question(x):
    select = "?x0"
    sparql = None
    for w in x:
        if w.pos == "nr" or w.pos == "x":
            e = f"cns_people:{w.token} cns:description ?x0"
            sparql = SPARQL_TEM.format(preamble=SPARQL_PREAMBLE, select=select, expression=INDENT + e)
            break
    return sparql


def where_is_from_question(x):
    select = "?x0"
    sparql = None
    for w in x:
        if w.pos == "nr" or w.pos == "x":
            e = f"cns_people:{w.token} cns:birthPlace ?x0"
            sparql = SPARQL_TEM.format(preamble=SPARQL_PREAMBLE, select=select, expression=INDENT + e)
            break
    return sparql


def whose_nationality_question(x):
    select = "?x0"
    sparql = None
    for w in x:
        if w.pos == "nr" or w.pos == "x":
            e = f"cns_people:{w.token} cns:ethnicity ?x0"
            sparql = SPARQL_TEM.format(preamble=SPARQL_PREAMBLE, select=select, expression=INDENT + e)
            break
    return sparql


if __name__ == "__main__":
    questions = [
        "谁是苑茵?",
        "丁洪奎是谁?",
        "苏进木来自哪里?",
        "苑茵是哪个族的?",
        "苑茵的民族是什么?",
    ]

    suggest_freq("苏进木", True)

    seg_lists = []
    # tokenizing questions
    for question in questions:
        words = pseg.cut(question)
        seg_list = [Word(word, flag) for word, flag in words]
        seg_lists.append(seg_list)

    # some rules for matching
    # TODO: customize your own rules here
    person = (W(pos="nr") | W(pos="x"))
    ethnic = (W("族") | W("民族"))

    # “ab” is Literal(“a”) + Literal(“b”)
    # “a *” is Star(Literal(“a”))
    rules = [
        Rule(condition=W(pos="r") + W("是") + person | person + W("是") + W(pos="r"), action=who_is_question),
        Rule(condition=person + W("来自") + Star(W("哪"), greedy=False), action=where_is_from_question),
        Rule(condition=person + Star(Any(), greedy=False) + ethnic, action=whose_nationality_question)
    ]

    # matching and querying
    for seg in seg_lists:
        for s in seg:
            print(s.token, s.pos)

        for rule in rules:
            query = rule.apply(seg)
            if query is None:
                print("Query not generated\n")
                continue
            print(query)

            if query:
                sparql_base.setQuery(query)
                sparql_base.setReturnFormat(JSON)
                results = sparql_base.query().convert()
                print(results)

                if not results["results"]["bindings"]:
                    print("No answer found")
                    continue

                for result in results["results"]["bindings"]:
                    print("Result: ", result["x0"]["value"])
