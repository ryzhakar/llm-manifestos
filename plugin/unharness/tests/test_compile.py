import pytest
from unharness.compile import compile_prompt, constitution_block, stack_view
from unharness.config import UnharnessError
from unharness.resolve import Document

DRY = Document("dry", "one home", "DRY TEXT", "a" * 64)
KISS = Document("kiss", None, "KISS TEXT\nsecond line", "b" * 64)
STACK = f"<stack>\ndry {'a' * 64} one home\nkiss {'b' * 64}\n</stack>"
INTERPLAY = f"{STACK}\n\n<interplay>\nThe elements agree.\n</interplay>\n"
COMMITMENTS = f"{STACK}\n\n<commitments>\nI must, and I will.\n</commitments>\n"


def test_the_prompt_is_the_preamble_the_constitution_and_the_two_session_files_without_their_stack_blocks():
    prompt = compile_prompt([DRY, KISS], "PREAMBLE", INTERPLAY, COMMITMENTS)

    assert prompt == (
        "<harness>\nPREAMBLE\n</harness>\n\n"
        "<constitution>\n"
        '<dry governs="one home">\nDRY TEXT\n</dry>\n'
        "<kiss>\nKISS TEXT\nsecond line\n</kiss>\n"
        "</constitution>\n\n"
        "<interplay>\nThe elements agree.\n</interplay>\n\n"
        "<commitments>\nI must, and I will.\n</commitments>"
    )


def test_the_stack_view_is_the_stack_block_with_one_sha256_line_per_element_then_the_constitution():
    view = stack_view([DRY, KISS])

    assert view == STACK + "\n\n" + constitution_block([DRY, KISS])


def stopped_by(interplay, commitments, documents=(DRY, KISS)) -> str:
    with pytest.raises(UnharnessError) as failure:
        compile_prompt(list(documents), "PREAMBLE", interplay, commitments)
    return str(failure.value)


def test_a_missing_session_file_stops_the_prompt_and_names_the_skill_that_writes_it():
    assert stopped_by(INTERPLAY, None) == ".manifestos/commitments.md is missing; run /compile-commitments"
    assert stopped_by(None, None) == ".manifestos/interplay.md is missing; run /compile-commitments"


def test_a_session_file_written_for_another_stack_names_each_changed_element():
    edited_dry = Document("dry", "one home", "EDITED", "c" * 64)
    added = Document("yagni", None, "YAGNI TEXT", "d" * 64)

    assert stopped_by(INTERPLAY, COMMITMENTS, [edited_dry, KISS]) == (
        ".manifestos/interplay.md is stale (changed: dry); run /compile-commitments"
    )
    assert stopped_by(INTERPLAY, COMMITMENTS, [DRY, KISS, added]) == (
        ".manifestos/interplay.md is stale (changed: yagni); run /compile-commitments"
    )
    assert stopped_by(INTERPLAY, COMMITMENTS, [DRY]) == (
        ".manifestos/interplay.md is stale (changed: kiss); run /compile-commitments"
    )


def test_a_session_file_written_for_the_same_elements_in_another_order_is_stale():
    assert stopped_by(INTERPLAY, COMMITMENTS, [KISS, DRY]) == (
        ".manifestos/interplay.md is stale (reordered); run /compile-commitments"
    )


def test_a_session_file_without_a_stack_block_is_stale():
    assert stopped_by("<interplay>\nx\n</interplay>\n", COMMITMENTS) == (
        ".manifestos/interplay.md has no <stack> block; run /compile-commitments"
    )


def test_a_double_quote_in_a_purpose_becomes_a_single_quote_in_governs():
    quoted = Document("dry", 'the "one home" rule', "DRY TEXT", "a" * 64)

    assert "<dry governs=\"the 'one home' rule\">" in constitution_block([quoted])
