from django.db import migrations


TABELAS = ("clinica_avaliacaofono", "clinica_dificuldadefono", "clinica_revisaoobjetivofono")


def instalar(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
        CREATE FUNCTION clinica_fono_preservar() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Avaliações e revisões existentes não podem ser alteradas ou excluídas';
        END; $$ LANGUAGE plpgsql
    """)
    for tabela in TABELAS:
        schema_editor.execute(
            f"CREATE TRIGGER preservar_fono BEFORE UPDATE OR DELETE ON {tabela} FOR EACH ROW EXECUTE FUNCTION clinica_fono_preservar()"
        )
    schema_editor.execute("""
        CREATE FUNCTION clinica_fono_origem_valida() RETURNS trigger AS $$
        DECLARE paciente_origem uuid; data_origem date;
        BEGIN
            IF NEW.origem_id IS NOT NULL THEN
                SELECT paciente_id, data INTO paciente_origem, data_origem
                FROM clinica_avaliacaofono WHERE id = NEW.origem_id;
                IF NOT FOUND OR paciente_origem IS DISTINCT FROM NEW.paciente_id
                   OR NEW.data < data_origem THEN
                    RAISE EXCEPTION 'Origem inválida para reavaliação';
                END IF;
            END IF;
            RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    schema_editor.execute(
        "CREATE TRIGGER fono_validar_origem BEFORE INSERT ON clinica_avaliacaofono FOR EACH ROW EXECUTE FUNCTION clinica_fono_origem_valida()"
    )


def remover(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP TRIGGER IF EXISTS fono_validar_origem ON clinica_avaliacaofono")
    schema_editor.execute("DROP FUNCTION IF EXISTS clinica_fono_origem_valida()")
    for tabela in TABELAS:
        schema_editor.execute(f"DROP TRIGGER IF EXISTS preservar_fono ON {tabela}")
    schema_editor.execute("DROP FUNCTION IF EXISTS clinica_fono_preservar()")


class Migration(migrations.Migration):
    dependencies = [("clinica", "0009_avaliacaofono_dificuldadefono_revisaoobjetivofono")]
    operations = [migrations.RunPython(instalar, remover)]
