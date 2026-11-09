"""Tests for the Python lexer that drives syntax highlighting and bracket matching."""
import random

import pytest

from mathdoer.languages.python.lexer import (
    IN_CONTINUED_DOUBLE_QUOTED_STRING,
    IN_CONTINUED_SINGLE_QUOTED_STRING,
    IN_TRIPLE_DOUBLE_QUOTED_STRING,
    IN_TRIPLE_SINGLE_QUOTED_STRING,
    NORMAL,
    lex_line,
)
from mathdoer.syntax import Token, TokenKind

COMMENT, STRING, NUMBER = TokenKind.COMMENT, TokenKind.STRING, TokenKind.NUMBER
KEYWORD, BUILTIN, OPERATOR = TokenKind.KEYWORD, TokenKind.BUILTIN, TokenKind.OPERATOR
FUNCTION_NAME, CLASS_NAME, DECORATOR = TokenKind.FUNCTION_NAME, TokenKind.CLASS_NAME, TokenKind.DECORATOR


def spans(text, state=NORMAL):
    """The lexed text as (the characters, their kind) pairs, and the state afterwards."""
    lexed = lex_line(text, state)
    return [(text[token.start:token.end], token.kind) for token in lexed.tokens], lexed.end_state


def only_tokens(text, state=NORMAL):
    return spans(text, state)[0]


def test_plain_code_has_operators_and_numbers_but_names_have_no_token():
    assert only_tokens("x = 1") == [("=", OPERATOR), ("1", NUMBER)]


def test_an_empty_line_has_no_tokens_and_keeps_its_state():
    assert spans("") == ([], NORMAL)
    assert spans("", IN_TRIPLE_DOUBLE_QUOTED_STRING) == ([], IN_TRIPLE_DOUBLE_QUOTED_STRING)


def test_keywords_include_the_constants():
    assert only_tokens("if x and not y:") == [("if", KEYWORD), ("and", KEYWORD), ("not", KEYWORD)]
    assert only_tokens("return True or False or None") == [
        ("return", KEYWORD), ("True", KEYWORD), ("or", KEYWORD), ("False", KEYWORD),
        ("or", KEYWORD), ("None", KEYWORD),
    ]


def test_builtin_functions_types_and_exceptions_are_builtins():
    assert only_tokens("print(len(x))") == [("print", BUILTIN), ("len", BUILTIN)]
    assert only_tokens("raise ValueError(str(e))") == [
        ("raise", KEYWORD), ("ValueError", BUILTIN), ("str", BUILTIN),
    ]


def test_names_that_merely_look_like_keywords_or_builtins_are_plain():
    assert only_tokens("iffy = printer + lenient") == [("=", OPERATOR), ("+", OPERATOR)]


def test_the_name_in_a_definition_is_marked_as_a_function_or_a_class():
    assert only_tokens("def area(r):") == [("def", KEYWORD), ("area", FUNCTION_NAME)]
    assert only_tokens("class Shape(Base):") == [("class", KEYWORD), ("Shape", CLASS_NAME)]
    assert only_tokens("async def go():") == [
        ("async", KEYWORD), ("def", KEYWORD), ("go", FUNCTION_NAME),
    ]


def test_a_defined_name_is_never_a_builtin():
    assert only_tokens("def print():") == [("def", KEYWORD), ("print", FUNCTION_NAME)]
    assert only_tokens("class list:") == [("class", KEYWORD), ("list", CLASS_NAME)]


def test_the_mark_for_a_definition_name_does_not_leak_to_later_names():
    assert only_tokens("def f(x, len):") == [
        ("def", KEYWORD), ("f", FUNCTION_NAME), ("len", BUILTIN),
    ]


def test_attribute_names_after_a_dot_are_plain():
    assert only_tokens("obj.print(x)") == []
    assert only_tokens("math.pi") == []
    assert only_tokens("obj . len") == []
    assert only_tokens("x.real + len(y)") == [("+", OPERATOR), ("len", BUILTIN)]


@pytest.mark.parametrize(
    "text",
    ["'abc'", '"abc"', "''", '""', "r'\\d'", 'b"x"', 'f"{x}"', "rb'x'", 'Rb"x"', "U'x'", 'BR"x"', 'fR"x"'],
)
def test_a_string_with_or_without_a_prefix_is_one_token(text):
    assert spans(text) == ([(text, STRING)], NORMAL)


def test_escaped_quotes_do_not_end_a_string():
    assert only_tokens("'it\\'s' + 1") == [("'it\\'s'", STRING), ("+", OPERATOR), ("1", NUMBER)]
    assert only_tokens('"say \\"hi\\""') == [('"say \\"hi\\""', STRING)]
    assert only_tokens("r'\\''") == [("r'\\''", STRING)]


def test_an_escaped_backslash_does_not_escape_the_quote_after_it():
    assert only_tokens("'a\\\\' + 1") == [("'a\\\\'", STRING), ("+", OPERATOR), ("1", NUMBER)]


def test_a_hash_inside_a_string_is_not_a_comment():
    assert only_tokens("'a # b'") == [("'a # b'", STRING)]


def test_a_comment_runs_to_the_end_of_the_line():
    assert only_tokens("x = 1  # a 'note' here") == [
        ("=", OPERATOR), ("1", NUMBER), ("# a 'note' here", COMMENT),
    ]
    assert only_tokens("'a' # c") == [("'a'", STRING), ("# c", COMMENT)]
    assert only_tokens("# whole line") == [("# whole line", COMMENT)]


def test_an_unterminated_single_quoted_string_ends_at_the_end_of_the_line():
    assert spans("x = 'abc") == ([("=", OPERATOR), ("'abc", STRING)], NORMAL)


@pytest.mark.parametrize(
    "text",
    ["0", "42", "3.14", ".5", "5.", "1e10", "1E-5", "2.5e+3", "1_000_000", "0xFF", "0b1010",
     "0o17", "3j", "1.5J", "0xdead_beef"],
)
def test_every_kind_of_number_is_one_token(text):
    assert spans(text) == ([(text, NUMBER)], NORMAL)


def test_digits_inside_a_name_do_not_make_a_number():
    assert only_tokens("x1 + y22") == [("+", OPERATOR)]


def test_a_number_ends_where_the_name_after_it_begins():
    assert only_tokens("2pi") == [("2", NUMBER)]


def test_operators_are_runs_of_operator_characters():
    assert only_tokens("a ** -b // c") == [("**", OPERATOR), ("-", OPERATOR), ("//", OPERATOR)]
    assert only_tokens("a<=b") == [("<=", OPERATOR)]
    assert only_tokens("a != b") == [("!=", OPERATOR)]


def test_brackets_commas_dots_and_colons_have_no_token():
    assert only_tokens("f(a, b)[0]{1: 2}") == [("0", NUMBER), ("1", NUMBER), ("2", NUMBER)]


def test_a_decorator_is_the_at_sign_and_its_dotted_name():
    assert only_tokens("@property") == [("@property", DECORATOR)]
    assert only_tokens("    @functools.wraps(f)") == [("@functools.wraps", DECORATOR)]


def test_an_at_sign_in_an_expression_is_an_operator():
    assert only_tokens("a @ b") == [("@", OPERATOR)]
    assert only_tokens("x = a @ b") == [("=", OPERATOR), ("@", OPERATOR)]


def test_unicode_names_are_names():
    assert only_tokens("π = 3") == [("=", OPERATOR), ("3", NUMBER)]


# ------------------------------------------------------- strings across lines

def test_a_triple_quoted_string_on_one_line_is_one_token():
    assert spans('"""abc"""') == ([('"""abc"""', STRING)], NORMAL)
    assert spans("'''abc'''") == ([("'''abc'''", STRING)], NORMAL)
    assert spans('"""a"b""c"""') == ([('"""a"b""c"""', STRING)], NORMAL)


def test_an_open_triple_quoted_string_carries_its_state_to_the_next_line():
    assert spans('x = """abc') == ([("=", OPERATOR), ('"""abc', STRING)], IN_TRIPLE_DOUBLE_QUOTED_STRING)
    assert spans("x = '''abc") == ([("=", OPERATOR), ("'''abc", STRING)], IN_TRIPLE_SINGLE_QUOTED_STRING)


def test_lines_inside_a_triple_quoted_string_are_all_string():
    state = IN_TRIPLE_DOUBLE_QUOTED_STRING
    assert spans("def f(x): # not code", state) == ([("def f(x): # not code", STRING)], state)
    assert spans("   ", state) == ([("   ", STRING)], state)
    assert spans("it's 'quoted'", state) == ([("it's 'quoted'", STRING)], state)


def test_a_triple_quoted_string_ends_at_its_own_delimiter_and_code_resumes():
    assert spans('end""" + 1', IN_TRIPLE_DOUBLE_QUOTED_STRING) == (
        [('end"""', STRING), ("+", OPERATOR), ("1", NUMBER)], NORMAL,
    )
    assert spans("end''' + 1", IN_TRIPLE_SINGLE_QUOTED_STRING) == (
        [("end'''", STRING), ("+", OPERATOR), ("1", NUMBER)], NORMAL,
    )


def test_the_other_kind_of_triple_quote_does_not_end_a_triple_quoted_string():
    state = IN_TRIPLE_DOUBLE_QUOTED_STRING
    assert spans("a ''' b", state) == ([("a ''' b", STRING)], state)


def test_an_escaped_triple_quote_does_not_end_the_string():
    state = IN_TRIPLE_DOUBLE_QUOTED_STRING
    assert spans('a \\""" b', state) == ([('a \\""" b', STRING)], state)


def test_a_backslash_at_the_end_of_a_single_quoted_string_continues_it():
    assert spans("'abc\\") == ([("'abc\\", STRING)], IN_CONTINUED_SINGLE_QUOTED_STRING)
    assert spans('"abc\\') == ([('"abc\\', STRING)], IN_CONTINUED_DOUBLE_QUOTED_STRING)
    assert spans("def'", IN_CONTINUED_SINGLE_QUOTED_STRING) == ([("def'", STRING)], NORMAL)
    assert spans('def"', IN_CONTINUED_DOUBLE_QUOTED_STRING) == ([('def"', STRING)], NORMAL)


def test_a_continued_string_that_runs_on_keeps_going_while_the_backslash_does():
    assert spans("more\\", IN_CONTINUED_SINGLE_QUOTED_STRING) == (
        [("more\\", STRING)], IN_CONTINUED_SINGLE_QUOTED_STRING,
    )
    assert spans("done", IN_CONTINUED_SINGLE_QUOTED_STRING) == ([("done", STRING)], NORMAL)


def test_a_doubled_backslash_at_the_end_does_not_continue_the_string():
    assert spans("'abc\\\\") == ([("'abc\\\\", STRING)], NORMAL)


# ------------------------------------------------------------------ invariants

ALPHABET = list("ab1 .'\"#\\(){}[]:,+-*=@\n") + ["def ", "class ", "r'", '"""', "'''", "0x", "e-"]


def random_line(generator):
    return "".join(generator.choice(ALPHABET) for _ in range(generator.randint(0, 30))).replace("\n", " ")


def test_tokens_are_sorted_non_overlapping_and_inside_the_line_for_random_text():
    generator = random.Random(2026)
    for _ in range(3000):
        text = random_line(generator)
        state = generator.choice([NORMAL, 1, 2, 3, 4])
        lexed = lex_line(text, state)
        assert 0 <= lexed.end_state <= 4
        previous_end = 0
        for token in lexed.tokens:
            assert isinstance(token, Token)
            assert previous_end <= token.start < token.end <= len(text), (text, state, lexed)
            previous_end = token.end


def test_every_state_is_reachable_and_returns_to_normal():
    seen = set()
    for text, state in [('"""a', NORMAL), ("'''a", NORMAL), ("'a\\", NORMAL), ('"a\\', NORMAL)]:
        seen.add(lex_line(text, state).end_state)
    assert seen == {
        IN_TRIPLE_DOUBLE_QUOTED_STRING, IN_TRIPLE_SINGLE_QUOTED_STRING,
        IN_CONTINUED_SINGLE_QUOTED_STRING, IN_CONTINUED_DOUBLE_QUOTED_STRING,
    }
    assert NORMAL == 0
