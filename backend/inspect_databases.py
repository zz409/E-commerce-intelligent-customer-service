import json
import sqlite3
from pathlib import Path

import sqlite_vec

import ladybug as lb

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"

SQLITE_PATH = DATA_DIR / "sqlite.sqlite"
GRAPH_PATH = DATA_DIR / "lbdb.lbdb"


def print_value(value):
    """完整输出数据，不截断长文本或向量。"""
    print(json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        default=str,
    ))


def quote_identifier(name):
    """为 SQLite 表名添加引号。"""
    return '"' + name.replace('"', '""') + '"'


def inspect_sqlite():
    print("\n========== SQLite ==========")

    if not SQLITE_PATH.exists():
        raise FileNotFoundError(SQLITE_PATH)

    # 只读连接，避免意外创建或修改数据库
    uri = SQLITE_PATH.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    try:
        conn.enable_load_extension(True)

        try:
            sqlite_vec.load(conn)
        finally:
            conn.enable_load_extension(False)

        tables = conn.execute("""
            SELECT m.name, m.sql
            FROM sqlite_master AS m
            JOIN pragma_table_list AS t ON t.name = m.name
            WHERE m.type = 'table'
              AND t.schema = 'main'
              AND t.type IN ('table', 'virtual')
              AND m.name NOT GLOB 'sqlite_*'
            ORDER BY m.name
        """).fetchall()

        for table in tables:
            name = table["name"]
            quoted_name = quote_identifier(name)

            print(f"\n{'=' * 60}")
            print(f"表名：{name}")

            print("\n建表语句：")
            print(table["sql"] or "无")

            print("\n字段结构：")
            for row in conn.execute(
                f"PRAGMA table_info({quoted_name})"
            ):
                print_value(dict(row))

            print("\n全部内容：")
            count = 0

            for row in conn.execute(
                f"SELECT * FROM {quoted_name}"
            ):
                record = {}

                for key in row.keys():
                    value = row[key]

                    if isinstance(value, bytes):
                        # vec0 的 FLOAT 向量以二进制形式返回
                        if name == "chunks" and key == "embedding":
                            value = json.loads(
                                conn.execute(
                                    "SELECT vec_to_json(?)",
                                    (value,),
                                ).fetchone()[0]
                            )
                        else:
                            # 其他二进制内容完整输出为十六进制
                            value = {
                                "type": "bytes",
                                "length": len(value),
                                "hex": value.hex(),
                            }

                    record[key] = value

                print_value(record)
                count += 1

            print(f"\n记录总数：{count}")
    finally:
        conn.close()


def quote_graph_identifier(name):
    """为 Ladybug 表名添加反引号。"""
    return "`" + name.replace("`", "``") + "`"


def graph_rows(conn, query):
    result = conn.execute(query)

    try:
        columns = result.get_column_names()

        while result.has_next():
            yield dict(zip(columns, result.get_next()))
    finally:
        result.close()


def inspect_graph():
    print("\n========== Ladybug ==========")

    if not GRAPH_PATH.exists():
        raise FileNotFoundError(GRAPH_PATH)

    db = lb.Database(str(GRAPH_PATH), read_only=True)

    try:
        conn = lb.Connection(db)

        try:
            tables = list(graph_rows(
                conn,
                "CALL show_tables() RETURN *",
            ))

            for table in tables:
                name = table["name"]
                table_type = table["type"]
                quoted_name = quote_graph_identifier(name)

                print(f"\n{'=' * 60}")
                print(f"表名：{name}")
                print(f"类型：{table_type}")

                # 转义过程参数中的单引号
                name_literal = name.replace("\\", "\\\\")
                name_literal = name_literal.replace("'", "\\'")

                print("\n字段结构：")
                for row in graph_rows(
                    conn,
                    f"CALL table_info('{name_literal}') RETURN *",
                ):
                    print_value(row)

                if table_type == "NODE":
                    query = (
                        f"MATCH (n:{quoted_name}) "
                        "RETURN n"
                    )
                elif table_type == "REL":
                    query = (
                        f"MATCH (a)-[r:{quoted_name}]->(b) "
                        "RETURN "
                        "id(a) AS source_node_id, "
                        "r AS relationship, "
                        "id(b) AS target_node_id"
                    )
                else:
                    print(f"暂不支持读取此类型：{table_type}")
                    continue

                print("\n全部内容：")
                count = 0

                for row in graph_rows(conn, query):
                    print_value(row)
                    count += 1

                print(f"\n记录总数：{count}")
        finally:
            conn.close()
    finally:
        db.close()


if __name__ == "__main__":
    inspect_sqlite()
    inspect_graph()
