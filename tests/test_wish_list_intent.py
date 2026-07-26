from services.intent import _parse_combined_intent_response
from services.wish_list import looks_like_wish_list_intent


def test_phrase_gate_detects_english_and_japanese():
    assert looks_like_wish_list_intent('I want to buy headphones 15000 yen')
    assert looks_like_wish_list_intent('買いたい コーヒーメーカー 8000円')
    assert looks_like_wish_list_intent('wishlist airpods 20000')
    assert looks_like_wish_list_intent('まだ買ってない 本 1200')


def test_phrase_gate_rejects_ordinary_expense():
    assert not looks_like_wish_list_intent('Lunch 1200 yen')
    assert not looks_like_wish_list_intent('ランチ 1200円')
    assert not looks_like_wish_list_intent('')


def test_parse_combined_intent_accepts_wish_list():
    assert _parse_combined_intent_response('{"intent": "wish_list"}') == 'wish_list'
    assert _parse_combined_intent_response('{"intent": "expense"}') == 'expense'
