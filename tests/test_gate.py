import pytest
from conftest import NOW, replies

from jarvis.gate import Gate, parse_decision


@pytest.mark.parametrize("reply,expected", [
    ("yes", "yes"), ("Yeah, send it.", "yes"), ("أيوه ابعت", "yes"), ("تمام", "yes"),
    ("no", "no"), ("لا", "no"), ("yes... no wait", "no"), ("استنى", "no"),
    ("", "unclear"), ("   ", "unclear"), ("hmm", "unclear"), ("yesterday", "unclear"),
    ("Go ahead!", "yes"), ("don’t", "no"), ("مش دلوقتي", "no"), ("not yet", "no"),
])
def test_parse_decision(reply, expected):
    assert parse_decision(reply) == expected


async def test_yes_approves(store):
    asked = []
    g = Gate(ask=replies("yes", record=asked), store=store, clock=lambda: NOW)
    assert await g.approve("mail.send", "Send to Ali: 'Thursday works.'", "{}") is True
    assert asked == ["Send to Ali: 'Thursday works.' Shall I go ahead?"]


async def test_no_declines(store):
    g = Gate(ask=replies("no"), store=store, clock=lambda: NOW)
    assert await g.approve("k", "d", "{}") is False


async def test_unclear_twice_is_no(store):
    asked = []
    g = Gate(ask=replies("hmm", "uh", record=asked), store=store, clock=lambda: NOW)
    assert await g.approve("mail.send", "Send to Ali.", "{}") is False
    assert len(asked) == 2 and "clear yes or no" in asked[1]


async def test_unclear_then_yes_approves(store):
    g = Gate(ask=replies("hmm", "yes"), store=store, clock=lambda: NOW)
    assert await g.approve("k", "d", "{}") is True


async def test_approve_does_not_log_but_record_does(store):
    g = Gate(ask=replies("yes"), store=store, clock=lambda: NOW)
    await g.approve("k", "d", "{}")
    assert store.actions(10) == []
    g.record("k", "d", "{}")
    a = store.actions(10)[0]
    assert (a.kind, a.summary, a.detail, a.at) == ("k", "d", "{}", NOW)


@pytest.mark.parametrize("reply", [
    "not ok", "I am not okay with that", "isn't ok", "ok dont", "dont send it",
    "can't confirm", "I would not say yes", "ok not now", "nah ok", "never, okay?",
    "مش تمام", "مش ماشي", "مش عايز ابعته", "ماتبعتش", "won't do it",
])
def test_negated_replies_are_no(reply):
    assert parse_decision(reply) == "no"


@pytest.mark.parametrize("reply", [
    "who said yes", "yes but change the subject first", "ok and add Sara in copy",
    "is it okay?", "تمام بس غير العنوان", "send it to Omar instead",
])
def test_yes_word_inside_a_longer_reply_is_not_a_yes(reply):
    assert parse_decision(reply) != "yes"


@pytest.mark.parametrize("reply", [
    "Yes please", "yes, go ahead", "ok jarvis", "Okay, send it. Thanks!",
    "أيوه يا جارفيس ابعته", "تمام ابعت", "sure, do it",
])
def test_plain_yes_with_politeness_is_yes(reply):
    assert parse_decision(reply) == "yes"
