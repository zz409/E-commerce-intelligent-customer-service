import sqlite3
from pathlib import Path

DATABASE_PATH = (
    Path(__file__).resolve().parent / "checkpoints.sqlite"
)


def main():
    if not DATABASE_PATH.is_file():
        print(f"数据库不存在：{DATABASE_PATH}")
        return

    # 只读打开数据库
    database_uri = DATABASE_PATH.as_uri() + "?mode=ro"

    with sqlite3.connect(database_uri, uri=True) as conn:
        # 允许通过字段名读取一列
        conn.row_factory = sqlite3.Row

        # 表名是代码中固定的，不接收外部输入
        for table_name in ("checkpoints", "writes"):
            print(f"\n========== 表：{table_name} ==========")

            cursor = conn.execute(
                f'SELECT * FROM "{table_name}"'
            )

            for index, row in enumerate(cursor, start=1):
                print(f"\n--- 第 {index} 条记录 ---")

                for column_name in row.keys():
                    value = row[column_name]

                    print(
                        f"{column_name} "
                        f"[{type(value).__name__}] = {value!r}"
                    )


if __name__ == "__main__":
    main()