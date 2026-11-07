from django.db import migrations


TABELAS = ("clinica_avaliacaofono", "clinica_planofono", "clinica_sessaofono")


def instalar(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
        CREATE FUNCTION clinica_correcao_paciente_valida() RETURNS trigger AS $$
        DECLARE paciente_anterior uuid;
        BEGIN
            IF NEW.corrige_id IS NOT NULL THEN
                EXECUTE format('SELECT paciente_id FROM %I WHERE id = $1', TG_TABLE_NAME)
                    INTO paciente_anterior USING NEW.corrige_id;
                IF paciente_anterior IS NULL OR paciente_anterior IS DISTINCT FROM NEW.paciente_id THEN
                    RAISE EXCEPTION 'Correção deve pertencer ao mesmo paciente';
                END IF;
            END IF;
            RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    for tabela in TABELAS:
        schema_editor.execute(
            f"CREATE TRIGGER validar_correcao BEFORE INSERT ON {tabela} FOR EACH ROW EXECUTE FUNCTION clinica_correcao_paciente_valida()"
        )


def remover(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for tabela in TABELAS:
        schema_editor.execute(f"DROP TRIGGER IF EXISTS validar_correcao ON {tabela}")
    schema_editor.execute("DROP FUNCTION IF EXISTS clinica_correcao_paciente_valida()")


class Migration(migrations.Migration):
    dependencies = [("clinica", "0015_avaliacaofono_corrige_planofono_corrige_and_more")]
    operations = [migrations.RunPython(instalar, remover)]
