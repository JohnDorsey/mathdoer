"""Tests for the editing commands, which work on lines of text with no text box involved."""
import random

import pytest

from mathdoer.languages import EditingRules
from mathdoer.line_editing import (
    Position,
    TextEdit,
    delete_lines,
    dedent,
    duplicate_lines,
    home_column,
    indent,
    insert_newline,
    move_lines,
    toggle_comment,
)

P = Position


def ends_with_colon(lines, line, column):
    return lines[line][:column].rstrip().endswith(":")


RULES = EditingRules(
    comment_prefix="#",
    opens_indented_block=ends_with_colon,
    bracket_pairs=(("(", ")"),),
    indent_width=4,
)


def apply(lines, edit):
    """The lines after the edit."""
    lines = list(lines)
    return lines[: edit.first_line] + list(edit.replacement) + lines[edit.last_line + 1:]


def result(lines, edit):
    return apply(lines, edit), edit.anchor, edit.cursor


# ------------------------------------------------------------------------- positions

def test_positions_order_by_line_then_column():
    assert P(0, 5) < P(1, 0) < P(1, 1)
    assert sorted([P(2, 0), P(0, 9), P(0, 1)]) == [P(0, 1), P(0, 9), P(2, 0)]


# ------------------------------------------------------------------------------ Tab

def test_tab_without_a_selection_inserts_spaces_up_to_the_next_tab_stop():
    assert result(["x"], indent(["x"], P(0, 0), P(0, 0), RULES)) == (["    x"], P(0, 4), P(0, 4))
    assert result(["ab"], indent(["ab"], P(0, 2), P(0, 2), RULES)) == (["ab  "], P(0, 4), P(0, 4))
    assert result(["abc"], indent(["abc"], P(0, 3), P(0, 3), RULES)) == (["abc "], P(0, 4), P(0, 4))
    assert result(["abcd"], indent(["abcd"], P(0, 4), P(0, 4), RULES)) == (["abcd    "], P(0, 8), P(0, 8))


def test_tab_in_the_middle_of_a_line_pushes_the_rest_along():
    assert result(["abcd"], indent(["abcd"], P(0, 1), P(0, 1), RULES)) == (["a   bcd"], P(0, 4), P(0, 4))


def test_tab_over_a_selection_inside_one_line_replaces_it_with_spaces():
    edit = indent(["hello"], P(0, 1), P(0, 4), RULES)
    assert result(["hello"], edit) == (["h   o"], P(0, 4), P(0, 4))


def test_a_selection_made_backwards_behaves_the_same():
    edit = indent(["hello"], P(0, 4), P(0, 1), RULES)
    assert result(["hello"], edit) == (["h   o"], P(0, 4), P(0, 4))


def test_tab_inside_the_leading_tabs_of_a_line_inserts_a_tab_character():
    assert result(["\tx"], indent(["\tx"], P(0, 1), P(0, 1), RULES)) == (["\t\tx"], P(0, 2), P(0, 2))
    assert result(["\tx"], indent(["\tx"], P(0, 0), P(0, 0), RULES)) == (["\t\tx"], P(0, 1), P(0, 1))


def test_tab_after_the_text_of_a_tab_indented_line_still_inserts_spaces():
    # The tab counts as four columns, and the text makes five, so three more reach column eight.
    assert result(["\tx"], indent(["\tx"], P(0, 2), P(0, 2), RULES)) == (["\tx   "], P(0, 5), P(0, 5))


def test_tab_over_several_lines_indents_every_line():
    lines = ["a", "b", "c"]
    edit = indent(lines, P(0, 0), P(2, 1), RULES)
    assert (edit.first_line, edit.last_line) == (0, 2)
    assert result(lines, edit) == (["    a", "    b", "    c"], P(0, 0), P(2, 5))


def test_a_selection_that_ends_at_the_start_of_a_line_leaves_that_line_alone():
    lines = ["a", "b", "c"]
    edit = indent(lines, P(0, 0), P(2, 0), RULES)
    assert (edit.first_line, edit.last_line) == (0, 1)
    assert result(lines, edit) == (["    a", "    b", "c"], P(0, 0), P(2, 0))


def test_empty_lines_are_not_indented():
    lines = ["a", "", "b"]
    assert result(lines, indent(lines, P(0, 0), P(2, 1), RULES))[0] == ["    a", "", "    b"]


def test_a_line_that_is_only_whitespace_is_indented_to_the_next_tab_stop():
    lines = ["a", "  ", "b"]
    assert result(lines, indent(lines, P(0, 0), P(2, 1), RULES))[0] == ["    a", "    ", "    b"]


def test_indenting_aligns_a_line_to_the_next_tab_stop():
    lines = ["  a", "     b", "c"]
    assert result(lines, indent(lines, P(0, 0), P(2, 1), RULES))[0] == ["    a", "        b", "    c"]


def test_a_tab_indented_line_gets_another_tab_when_several_lines_are_indented():
    lines = ["\ta", "b"]
    assert result(lines, indent(lines, P(0, 0), P(1, 1), RULES))[0] == ["\t\ta", "    b"]


def test_indenting_keeps_the_ends_of_the_selection_on_their_text():
    lines = ["abcd", "efgh"]
    assert result(lines, indent(lines, P(0, 2), P(1, 3), RULES)) == (
        ["    abcd", "    efgh"], P(0, 6), P(1, 7),
    )


def test_a_selection_start_at_the_beginning_of_a_line_stays_there():
    lines = ["abc", "def"]
    edit = indent(lines, P(0, 0), P(1, 3), RULES)
    assert edit.anchor == P(0, 0)


def test_indenting_only_empty_lines_changes_nothing():
    assert indent(["", "", ""], P(0, 0), P(2, 0), RULES) is None
    assert indent(["", "", ""], P(0, 0), P(1, 0), RULES) is None


# ------------------------------------------------------------------------- Shift+Tab

def test_shift_tab_removes_one_level_from_the_current_line():
    assert result(["    a"], dedent(["    a"], P(0, 5), P(0, 5), RULES)) == (["a"], P(0, 1), P(0, 1))


def test_a_caret_inside_the_removed_whitespace_goes_to_the_start_of_the_line():
    assert result(["    a"], dedent(["    a"], P(0, 2), P(0, 2), RULES)) == (["a"], P(0, 0), P(0, 0))
    assert result(["  a"], dedent(["  a"], P(0, 1), P(0, 1), RULES)) == (["a"], P(0, 0), P(0, 0))


@pytest.mark.parametrize(
    "before, after",
    [("    a", "a"), ("      a", "    a"), ("   a", "a"), ("        a", "    a"), ("          a", "        a"),
     (" a", "a")],
)
def test_shift_tab_goes_back_to_the_previous_tab_stop(before, after):
    assert apply([before], dedent([before], P(0, 0), P(0, 0), RULES)) == [after]


def test_shift_tab_removes_one_tab_character():
    assert result(["\t\ta"], dedent(["\t\ta"], P(0, 2), P(0, 2), RULES)) == (["\ta"], P(0, 1), P(0, 1))


def test_shift_tab_on_a_line_with_nothing_to_remove_changes_nothing():
    assert dedent(["a"], P(0, 1), P(0, 1), RULES) is None
    assert dedent([""], P(0, 0), P(0, 0), RULES) is None


def test_shift_tab_dedents_every_line_of_a_selection():
    lines = ["    a", "        b", "c"]
    edit = dedent(lines, P(0, 0), P(2, 1), RULES)
    assert result(lines, edit) == (["a", "    b", "c"], P(0, 0), P(2, 1))


def test_shift_tab_leaves_alone_a_last_line_the_selection_only_touches_at_its_start():
    lines = ["    a", "    b"]
    edit = dedent(lines, P(0, 0), P(1, 0), RULES)
    assert (edit.first_line, edit.last_line) == (0, 0)
    assert apply(lines, edit) == ["a", "    b"]


def test_shift_tab_on_a_part_of_one_line_dedents_the_whole_line():
    assert apply(["    hello"], dedent(["    hello"], P(0, 5), P(0, 8), RULES)) == ["hello"]


def test_shift_tab_moves_selection_ends_with_their_text_but_never_before_the_line():
    lines = ["    abc", "    def"]
    edit = dedent(lines, P(0, 6), P(1, 2), RULES)
    assert (edit.anchor, edit.cursor) == (P(0, 2), P(1, 0))


# ------------------------------------------------------------------------------ Enter

def test_enter_at_the_end_of_a_line_starts_an_empty_line():
    assert result(["x = 1"], insert_newline(["x = 1"], P(0, 5), P(0, 5), RULES)) == (
        ["x = 1", ""], P(1, 0), P(1, 0),
    )


def test_enter_keeps_the_indentation_of_the_line():
    assert result(["    x = 1"], insert_newline(["    x = 1"], P(0, 9), P(0, 9), RULES)) == (
        ["    x = 1", "    "], P(1, 4), P(1, 4),
    )


def test_enter_after_a_colon_adds_one_level():
    assert result(["if x:"], insert_newline(["if x:"], P(0, 5), P(0, 5), RULES)) == (
        ["if x:", "    "], P(1, 4), P(1, 4),
    )
    assert result(["    if x:"], insert_newline(["    if x:"], P(0, 9), P(0, 9), RULES)) == (
        ["    if x:", "        "], P(1, 8), P(1, 8),
    )


def test_enter_after_a_colon_in_a_tab_indented_line_adds_a_tab():
    assert result(["\tif x:"], insert_newline(["\tif x:"], P(0, 6), P(0, 6), RULES)) == (
        ["\tif x:", "\t\t"], P(1, 2), P(1, 2),
    )


def test_enter_in_the_middle_of_a_line_splits_it():
    assert result(["foo bar"], insert_newline(["foo bar"], P(0, 3), P(0, 3), RULES)) == (
        ["foo", "bar"], P(1, 0), P(1, 0),
    )


def test_the_second_half_of_a_split_line_gets_the_indentation_of_the_first():
    assert result(["    foo bar"], insert_newline(["    foo bar"], P(0, 7), P(0, 7), RULES)) == (
        ["    foo", "    bar"], P(1, 4), P(1, 4),
    )


def test_enter_inside_the_indentation_just_splits_the_line_and_adds_nothing():
    assert result(["        x"], insert_newline(["        x"], P(0, 4), P(0, 4), RULES)) == (
        ["", "    x"], P(1, 0), P(1, 0),
    )


def test_enter_at_the_start_of_an_indented_line_pushes_it_down_unchanged():
    assert result(["    x"], insert_newline(["    x"], P(0, 0), P(0, 0), RULES)) == (
        ["", "    x"], P(1, 0), P(1, 0),
    )


def test_enter_inside_the_indentation_does_not_ask_whether_a_block_opens():
    asked = []
    rules = EditingRules("#", lambda lines, line, column: asked.append(column) or True, (), 4)
    insert_newline(["    if x:"], P(0, 2), P(0, 2), rules)
    assert asked == []


def test_enter_on_a_line_of_only_whitespace_clears_it_and_carries_the_indentation():
    assert result(["    "], insert_newline(["    "], P(0, 4), P(0, 4), RULES)) == (
        ["", "    "], P(1, 4), P(1, 4),
    )


def test_enter_over_a_selection_replaces_it():
    assert result(["abcdef"], insert_newline(["abcdef"], P(0, 1), P(0, 4), RULES)) == (
        ["a", "ef"], P(1, 0), P(1, 0),
    )
    assert result(["abcdef"], insert_newline(["abcdef"], P(0, 4), P(0, 1), RULES))[0] == ["a", "ef"]


def test_enter_over_a_selection_across_lines_joins_the_ends():
    lines = ["abc", "def", "ghi"]
    edit = insert_newline(lines, P(0, 1), P(2, 2), RULES)
    assert (edit.first_line, edit.last_line) == (0, 2)
    assert result(lines, edit) == (["a", "i"], P(1, 0), P(1, 0))


def test_enter_after_a_colon_ignores_what_follows_the_caret():
    assert result(["if x:  # c"], insert_newline(["if x:  # c"], P(0, 5), P(0, 5), RULES)) == (
        ["if x:", "    # c"], P(1, 4), P(1, 4),
    )


def test_the_rule_for_blocks_is_asked_about_the_text_before_the_start_of_the_selection():
    asked = []

    def record(lines, line, column):
        asked.append((list(lines), line, column))
        return False

    rules = EditingRules("#", record, (("(", ")"),), 4)
    lines = ["a", "bcdef"]
    insert_newline(lines, P(1, 4), P(1, 2), rules)
    assert asked == [(lines, 1, 2)]


def test_enter_changes_only_the_lines_it_touches():
    lines = ["a", "b", "c"]
    edit = insert_newline(lines, P(1, 1), P(1, 1), RULES)
    assert (edit.first_line, edit.last_line) == (1, 1)


# ---------------------------------------------------------------------- toggle comment

def test_commenting_a_line_adds_the_prefix_and_a_space():
    assert result(["x = 1"], toggle_comment(["x = 1"], P(0, 3), P(0, 3), RULES)) == (
        ["# x = 1"], P(0, 5), P(0, 5),
    )


def test_a_caret_at_the_start_of_the_text_stays_with_the_text():
    assert result(["x"], toggle_comment(["x"], P(0, 0), P(0, 0), RULES))[1:] == (P(0, 2), P(0, 2))


def test_uncommenting_a_line_removes_the_prefix_and_the_space():
    assert result(["# x = 1"], toggle_comment(["# x = 1"], P(0, 7), P(0, 7), RULES)) == (
        ["x = 1"], P(0, 5), P(0, 5),
    )


def test_a_caret_inside_the_removed_prefix_goes_to_the_start_of_the_text():
    assert result(["# x"], toggle_comment(["# x"], P(0, 1), P(0, 1), RULES))[1:] == (P(0, 0), P(0, 0))


def test_uncommenting_works_without_the_space():
    assert apply(["#x = 1"], toggle_comment(["#x = 1"], P(0, 0), P(0, 0), RULES)) == ["x = 1"]


def test_the_prefix_goes_at_the_indentation_of_the_line():
    assert apply(["    x = 1"], toggle_comment(["    x = 1"], P(0, 6), P(0, 6), RULES)) == ["    # x = 1"]
    assert apply(["    # x = 1"], toggle_comment(["    # x = 1"], P(0, 6), P(0, 6), RULES)) == ["    x = 1"]


def test_several_lines_get_the_prefix_at_the_shallowest_indentation():
    lines = ["a", "  b"]
    assert apply(lines, toggle_comment(lines, P(0, 0), P(1, 3), RULES)) == ["# a", "#   b"]
    lines = ["    a", "      b"]
    assert apply(lines, toggle_comment(lines, P(0, 0), P(1, 3), RULES)) == ["    # a", "    #   b"]


def test_blank_lines_among_several_are_left_alone():
    lines = ["a", "", "  ", "b"]
    assert apply(lines, toggle_comment(lines, P(0, 0), P(3, 1), RULES)) == ["# a", "", "  ", "# b"]


def test_a_mix_of_commented_and_plain_lines_gets_commented_again():
    lines = ["# a", "b"]
    assert apply(lines, toggle_comment(lines, P(0, 0), P(1, 1), RULES)) == ["# # a", "# b"]


def test_when_every_line_is_commented_they_are_all_uncommented():
    lines = ["# a", "  # b", "", "#c"]
    assert apply(lines, toggle_comment(lines, P(0, 0), P(3, 2), RULES)) == ["a", "  b", "", "c"]


def test_a_single_blank_line_is_commented():
    assert result([""], toggle_comment([""], P(0, 0), P(0, 0), RULES)) == (["# "], P(0, 2), P(0, 2))


def test_several_blank_lines_have_nothing_to_comment():
    assert toggle_comment(["", "  "], P(0, 0), P(1, 2), RULES) is None
    assert toggle_comment(["", "", ""], P(0, 0), P(2, 0), RULES) is None


def test_a_selection_from_the_start_of_one_blank_line_to_the_start_of_the_next_is_one_line():
    assert apply(["", ""], toggle_comment(["", ""], P(0, 0), P(1, 0), RULES)) == ["# ", ""]


def test_a_selection_that_ends_at_the_start_of_a_line_leaves_that_line_alone_when_commenting():
    lines = ["a", "b", "c"]
    edit = toggle_comment(lines, P(0, 0), P(2, 0), RULES)
    assert (edit.first_line, edit.last_line) == (0, 1)
    assert apply(lines, edit) == ["# a", "# b", "c"]


def test_the_prefix_comes_from_the_language():
    rules = EditingRules("//", ends_with_colon, (("(", ")"),), 4)
    assert apply(["x"], toggle_comment(["x"], P(0, 0), P(0, 0), rules)) == ["// x"]
    assert apply(["// x"], toggle_comment(["// x"], P(0, 0), P(0, 0), rules)) == ["x"]


def test_both_ends_of_a_selection_move_with_the_inserted_prefix():
    lines = ["ab", "cd"]
    assert result(lines, toggle_comment(lines, P(0, 1), P(1, 2), RULES))[1:] == (P(0, 3), P(1, 4))


def test_a_selection_that_starts_at_the_beginning_of_the_text_keeps_the_new_marker_inside_it():
    lines = ["a", "b"]
    assert result(lines, toggle_comment(lines, P(0, 0), P(1, 1), RULES))[1:] == (P(0, 0), P(1, 3))
    assert result(lines, toggle_comment(lines, P(1, 1), P(0, 0), RULES))[1:] == (P(1, 3), P(0, 0))


def test_the_same_holds_when_the_lines_are_indented():
    lines = ["    a", "    b"]
    assert result(lines, toggle_comment(lines, P(0, 4), P(1, 5), RULES))[1:] == (P(0, 4), P(1, 7))


def test_a_selection_that_ends_at_the_beginning_of_the_text_takes_the_marker_in():
    lines = ["a", "b"]
    assert result(lines, toggle_comment(lines, P(0, 0), P(1, 0), RULES))[1:] == (P(0, 0), P(1, 0))
    lines = ["a", "    b", "c"]
    assert result(lines, toggle_comment(lines, P(0, 0), P(1, 4), RULES))[1:] == (P(0, 0), P(1, 6))


def test_both_ends_of_a_selection_move_back_with_the_removed_prefix():
    lines = ["# ab", "# cd"]
    assert result(lines, toggle_comment(lines, P(0, 3), P(1, 4), RULES))[1:] == (P(0, 1), P(1, 2))


# ---------------------------------------------------------------------- duplicate lines

def test_duplicating_a_line_copies_it_below_and_moves_the_caret_to_the_copy():
    lines = ["a", "b"]
    edit = duplicate_lines(lines, P(0, 1), P(0, 1))
    assert (edit.first_line, edit.last_line) == (0, 0)
    assert result(lines, edit) == (["a", "a", "b"], P(1, 1), P(1, 1))


def test_duplicating_several_lines_copies_the_whole_block_and_selects_the_copy():
    lines = ["a", "b", "c"]
    assert result(lines, duplicate_lines(lines, P(0, 0), P(1, 1))) == (
        ["a", "b", "a", "b", "c"], P(2, 0), P(3, 1),
    )


def test_a_selection_that_ends_at_the_start_of_a_line_does_not_duplicate_that_line():
    lines = ["a", "b", "c"]
    assert result(lines, duplicate_lines(lines, P(0, 0), P(2, 0))) == (
        ["a", "b", "a", "b", "c"], P(2, 0), P(4, 0),
    )


def test_duplicating_the_last_line():
    assert result(["a"], duplicate_lines(["a"], P(0, 1), P(0, 1))) == (["a", "a"], P(1, 1), P(1, 1))


def test_duplicating_with_a_selection_inside_one_line_copies_the_whole_line():
    assert result(["hello"], duplicate_lines(["hello"], P(0, 1), P(0, 3))) == (
        ["hello", "hello"], P(1, 1), P(1, 3),
    )


# ------------------------------------------------------------------------- move lines

def test_moving_a_line_up_swaps_it_with_the_one_above():
    lines = ["a", "b", "c"]
    edit = move_lines(lines, P(1, 1), P(1, 1), -1)
    assert (edit.first_line, edit.last_line) == (0, 1)
    assert result(lines, edit) == (["b", "a", "c"], P(0, 1), P(0, 1))


def test_moving_a_line_down_swaps_it_with_the_one_below():
    lines = ["a", "b", "c"]
    assert result(lines, move_lines(lines, P(0, 0), P(0, 0), 1)) == (["b", "a", "c"], P(1, 0), P(1, 0))


def test_the_first_line_cannot_move_up_and_the_last_cannot_move_down():
    assert move_lines(["a", "b"], P(0, 0), P(0, 0), -1) is None
    assert move_lines(["a", "b"], P(1, 0), P(1, 0), 1) is None
    assert move_lines(["a"], P(0, 0), P(0, 0), 1) is None


def test_a_block_of_lines_moves_together_and_stays_selected():
    lines = ["a", "b", "c", "d"]
    assert result(lines, move_lines(lines, P(1, 0), P(2, 1), -1)) == (["b", "c", "a", "d"], P(0, 0), P(1, 1))
    assert result(lines, move_lines(lines, P(0, 0), P(1, 1), 1)) == (["c", "a", "b", "d"], P(1, 0), P(2, 1))


def test_a_selection_that_ends_at_the_start_of_a_line_moves_only_the_lines_it_covers():
    lines = ["a", "b", "c"]
    assert result(lines, move_lines(lines, P(0, 0), P(1, 0), 1)) == (["b", "a", "c"], P(1, 0), P(2, 0))


def test_a_selection_ending_at_the_start_of_the_last_line_ends_at_the_end_of_the_document_when_moved_down():
    lines = ["a", "b", "c"]
    # "b" is selected by going to the start of "c"; moving it below "c" leaves no next line.
    assert result(lines, move_lines(lines, P(1, 0), P(2, 0), 1)) == (["a", "c", "b"], P(2, 0), P(2, 1))


def test_moving_a_line_keeps_the_caret_column():
    lines = ["abc", "defgh"]
    assert result(lines, move_lines(lines, P(1, 4), P(1, 4), -1))[1:] == (P(0, 4), P(0, 4))


# ------------------------------------------------------------------------ delete lines

def test_deleting_a_line_puts_the_caret_in_the_same_column_of_the_next_line():
    lines = ["a", "b", "c"]
    assert result(lines, delete_lines(lines, P(1, 1), P(1, 1))) == (["a", "c"], P(1, 1), P(1, 1))


def test_the_caret_column_is_limited_to_the_length_of_the_next_line():
    lines = ["abc", "de", "f"]
    assert result(lines, delete_lines(lines, P(0, 3), P(0, 3))) == (["de", "f"], P(0, 2), P(0, 2))


def test_deleting_the_last_line_moves_the_caret_to_the_line_above():
    assert result(["a", "b"], delete_lines(["a", "b"], P(1, 1), P(1, 1))) == (["a"], P(0, 1), P(0, 1))


def test_deleting_the_only_line_leaves_one_empty_line():
    assert result(["abc"], delete_lines(["abc"], P(0, 2), P(0, 2))) == ([""], P(0, 0), P(0, 0))


def test_deleting_several_lines():
    lines = ["a", "b", "c", "d"]
    assert result(lines, delete_lines(lines, P(0, 0), P(2, 1))) == (["d"], P(0, 1), P(0, 1))
    assert result(lines, delete_lines(lines, P(1, 0), P(3, 1))) == (["a"], P(0, 1), P(0, 1))


def test_deleting_all_the_lines_leaves_one_empty_line():
    lines = ["a", "b"]
    assert result(lines, delete_lines(lines, P(0, 0), P(1, 1))) == ([""], P(0, 0), P(0, 0))


def test_a_selection_that_ends_at_the_start_of_a_line_does_not_delete_that_line():
    lines = ["a", "b", "c"]
    assert result(lines, delete_lines(lines, P(0, 0), P(2, 0))) == (["c"], P(0, 0), P(0, 0))


def test_deleting_a_line_changes_only_the_lines_around_it():
    lines = ["a", "b", "c", "d"]
    edit = delete_lines(lines, P(1, 0), P(1, 0))
    assert (edit.first_line, edit.last_line) == (1, 2)


# ---------------------------------------------------------------------------------- Home

@pytest.mark.parametrize(
    "line, column, expected",
    [
        ("    x = 1", 8, 4),
        ("    x = 1", 4, 0),
        ("    x = 1", 0, 4),
        ("    x = 1", 2, 4),
        ("x", 1, 0),
        ("x", 0, 0),
        ("   ", 3, 0),
        ("   ", 1, 3),
        ("   ", 0, 3),
        ("\tx", 2, 1),
        ("\tx", 1, 0),
        ("", 0, 0),
    ],
)
def test_home_goes_to_the_first_character_that_is_not_whitespace_and_then_to_the_start(
    line, column, expected
):
    assert home_column(line, column) == expected


# ----------------------------------------------------------------------- round trips

def random_document(generator):
    lines = []
    for _ in range(generator.randint(1, 8)):
        indentation = generator.choice(["", "", "  ", "    ", "        ", "\t"])
        text = generator.choice(["", "a", "b = 2", "if x:", "# note", "foo(bar)", "x"])
        lines.append(indentation + text)
    return lines


def random_selection(generator, lines):
    def position():
        line = generator.randrange(len(lines))
        return P(line, generator.randint(0, len(lines[line])))

    first = position()
    return first, first if generator.random() < 0.4 else position()


def test_moving_down_and_then_up_restores_the_text_and_the_selection():
    generator = random.Random(11)
    for _ in range(500):
        lines = random_document(generator)
        anchor, cursor = random_selection(generator, lines)
        down = move_lines(lines, anchor, cursor, 1)
        if down is None:
            continue
        moved = apply(lines, down)
        back = move_lines(moved, down.anchor, down.cursor, -1)
        assert back is not None
        assert apply(moved, back) == lines
        # A selection that ended at the start of the last line has the same lines selected
        # afterwards, but is written as ending at the end of the document instead.
        end, start = max(anchor, cursor), min(anchor, cursor)
        if end == P(len(lines) - 1, 0) and start.line != end.line:
            continue
        assert (back.anchor, back.cursor) == (anchor, cursor)


def test_toggling_a_comment_three_times_is_the_same_as_toggling_it_once():
    generator = random.Random(12)
    for _ in range(500):
        lines = random_document(generator)
        selection = random_selection(generator, lines)
        once = toggle_comment(lines, *selection, RULES)
        if once is None:
            continue
        text, anchor, cursor = apply(lines, once), once.anchor, once.cursor
        for _ in range(2):
            edit = toggle_comment(text, anchor, cursor, RULES)
            text, anchor, cursor = apply(text, edit), edit.anchor, edit.cursor
        assert (text, anchor, cursor) == (apply(lines, once), once.anchor, once.cursor), lines


def test_commenting_and_then_uncommenting_restores_the_text_and_the_selection():
    # Uncommenting first cannot promise that: the markers may have been at different columns,
    # and a caret just before a marker and one just after it both end up before the text.
    generator = random.Random(12)
    checked = 0
    for _ in range(500):
        lines = random_document(generator)
        anchor, cursor = random_selection(generator, lines)
        first = toggle_comment(lines, anchor, cursor, RULES)
        if first is None:
            continue
        toggled = apply(lines, first)
        if sum(map(len, toggled)) < sum(map(len, lines)):
            continue  # that took comments off
        second = toggle_comment(toggled, first.anchor, first.cursor, RULES)
        assert apply(toggled, second) == lines
        assert (second.anchor, second.cursor) == (anchor, cursor), (lines, anchor, cursor)
        checked += 1
    assert checked > 100


def test_duplicating_and_then_deleting_the_copy_restores_the_text():
    generator = random.Random(13)
    for _ in range(500):
        lines = random_document(generator)
        anchor, cursor = random_selection(generator, lines)
        duplicated = duplicate_lines(lines, anchor, cursor)
        doubled = apply(lines, duplicated)
        removed = delete_lines(doubled, duplicated.anchor, duplicated.cursor)
        assert apply(doubled, removed) == lines


def test_every_edit_replaces_at_least_one_line_and_stays_inside_the_document():
    generator = random.Random(14)
    commands = [
        lambda lines, a, c: indent(lines, a, c, RULES),
        lambda lines, a, c: dedent(lines, a, c, RULES),
        lambda lines, a, c: insert_newline(lines, a, c, RULES),
        lambda lines, a, c: toggle_comment(lines, a, c, RULES),
        lambda lines, a, c: duplicate_lines(lines, a, c),
        lambda lines, a, c: move_lines(lines, a, c, 1),
        lambda lines, a, c: move_lines(lines, a, c, -1),
        lambda lines, a, c: delete_lines(lines, a, c),
    ]
    for _ in range(400):
        lines = random_document(generator)
        anchor, cursor = random_selection(generator, lines)
        for command in commands:
            edit = command(lines, anchor, cursor)
            if edit is None:
                continue
            assert isinstance(edit, TextEdit)
            assert 0 <= edit.first_line <= edit.last_line < len(lines)
            assert len(edit.replacement) >= 1
            new_lines = apply(lines, edit)
            for position in (edit.anchor, edit.cursor):
                assert 0 <= position.line < len(new_lines)
                assert 0 <= position.column <= len(new_lines[position.line])
