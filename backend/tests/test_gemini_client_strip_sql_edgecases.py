from backend.llm.gemini_client import strip_sql


def test_strip_sql_with_extra_backticks_in_fence():
    text = "```sql\nSELECT 1;\n```\n"
    assert strip_sql(text) == "SELECT 1;"


def test_strip_sql_empty_code_block_returns_empty_string():
    text = "```sql\n\n```"
    assert strip_sql(text) == ""

