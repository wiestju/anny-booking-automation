from auth.session import AnnySession

ID = "c1e9143a-8a40-461f-9c0e-91ca87986310"


def test_extracts_id_from_old_format():
    html = f'[..."customer-accounts","{ID}"...]'
    assert AnnySession._extract_customer_account_id(html) == ID


def test_extracts_id_from_collection_key():
    html = (f'"api-collection:customer-accounts-{ID}-liked-resources_home-liked-resources_collection":710')
    assert AnnySession._extract_customer_account_id(html) == ID


def test_returns_none_without_id():
    assert AnnySession._extract_customer_account_id('"api:customer-accounts":103') is None
