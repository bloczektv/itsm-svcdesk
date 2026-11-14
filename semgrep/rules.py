# ai-generated: 70% - Claude Code drafted the test cases; I checked each annotation against the rule
import sqlite3

_conn = sqlite3.connect(":memory:")


def sql_cases(query, state):
    # ruleid: svcdesk-sql-not-literal
    _conn.execute(query, [state])
    # ok: svcdesk-sql-not-literal
    _conn.execute("SELECT * FROM tickets WHERE id = ?", (state,))


async def url_cases(client, base, q):
    # ruleid: svcdesk-upstream-url-fstring
    await client.get(f"{base}/search", params={"q": q})
    # ok: svcdesk-upstream-url-fstring
    await client.get("http://kb-index:8080/search", params={"q": q})
