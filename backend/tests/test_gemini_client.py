from backend.llm.gemini_client import strip_sql, build_sql_system_prompt, build_answer_prompt


def test_strip_sql_extracts_fenced_sql_block():
    text = "Here you go:\n```sql\nSELECT * FROM customers;\n```\nThanks"
    assert strip_sql(text) == "SELECT * FROM customers;"


def test_strip_sql_handles_non_sql_fence():
    text = "```\nSELECT id\nFROM t;\n```"
    assert strip_sql(text) == "SELECT id\nFROM t;"


def test_strip_sql_returns_raw_text_when_no_fence():
    text = "SELECT * FROM t;"
    assert strip_sql(text) == "SELECT * FROM t;"


def test_build_sql_system_prompt_includes_schema_prompt():
    schema_context = {"schema_prompt": "Table: customers\n- id (int) sample: [1]"}
    prompt = build_sql_system_prompt(schema_context)
    assert "expert PostgreSQL analyst" in prompt
    assert "Schema:" in prompt
    assert "Table: customers" in prompt


def test_build_answer_prompt_includes_question_sql_and_results():
    prompt = build_answer_prompt(
        question="Q?",
        sql="SELECT 1",
        results=[{"x": 1}],
    )
    assert "User question:" in prompt
    assert "Q?" in prompt
    assert "SQL:" in prompt
    assert "SELECT 1" in prompt
    assert "Query results (JSON):" in prompt
    assert "[{\"x\": 1}]" in prompt

