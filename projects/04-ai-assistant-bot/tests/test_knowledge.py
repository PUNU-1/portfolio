from bot.knowledge import KnowledgeBase, stem, stems


def test_stem_ignores_endings():
    assert stem("находится") == stem("находитесь")
    assert stem("цена") == stem("цены")
    assert stem("записаться") == stem("запись")


def test_stopwords_are_dropped():
    assert stems("Как мне это сделать") == {"сдел"}


def test_comments_are_not_searchable(kb):
    assert all(not chunk.startswith("#") for chunk in kb.chunks)
    assert "ДЕМО-ДАННЫЕ" not in " ".join(kb.chunks)


def test_finds_address(kb):
    assert "ул. Примерная, 1" in kb.search("где вы находитесь?")[0]


def test_finds_price_of_specific_service(kb):
    assert "1000 рублей" in kb.search("сколько стоит детская стрижка")[0]
    assert "2300 рублей" in kb.search("цена комплекса стрижка с бородой")[0]


def test_finds_working_hours(kb):
    assert "с 10:00 до 20:00" in kb.search("во сколько вы открываетесь")[0]


def test_nothing_found_for_offtopic(kb):
    assert kb.search("расскажи про погоду на марсе") == []


def test_limit_of_results(kb):
    assert len(kb.search("стрижка", limit=2)) == 2


def test_blocks_split_by_blank_lines():
    base = KnowledgeBase("Первый блок про кофе.\n\nВторой блок про чай.\n\n# комментарий\n\nТретий про сок.")
    assert len(base.chunks) == 3
    assert base.search("чай") == ["Второй блок про чай."]
