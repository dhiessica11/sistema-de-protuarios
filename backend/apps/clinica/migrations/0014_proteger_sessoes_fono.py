from django.db import migrations


def instalar(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "CREATE TRIGGER preservar_fono BEFORE UPDATE OR DELETE ON clinica_sessaofono FOR EACH ROW EXECUTE FUNCTION clinica_fono_preservar()"
    )
    schema_editor.execute("""
        CREATE FUNCTION clinica_sessao_objetivo_valido() RETURNS trigger AS $$
        DECLARE paciente_objetivo uuid;
        BEGIN
            IF NEW.objetivo_id IS NOT NULL THEN
                SELECT p.paciente_id INTO paciente_objetivo
                FROM clinica_itemplanofono i JOIN clinica_planofono p ON p.id = i.plano_id
                WHERE i.id = NEW.objetivo_id;
                IF NOT FOUND OR paciente_objetivo IS DISTINCT FROM NEW.paciente_id THEN
                    RAISE EXCEPTION 'Objetivo deve pertencer ao paciente da sessão';
                END IF;
            END IF;
            RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    schema_editor.execute(
        "CREATE TRIGGER sessao_validar_objetivo BEFORE INSERT ON clinica_sessaofono FOR EACH ROW EXECUTE FUNCTION clinica_sessao_objetivo_valido()"
    )


def remover(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP TRIGGER IF EXISTS sessao_validar_objetivo ON clinica_sessaofono")
    schema_editor.execute("DROP FUNCTION IF EXISTS clinica_sessao_objetivo_valido()")
    schema_editor.execute("DROP TRIGGER IF EXISTS preservar_fono ON clinica_sessaofono")


class Migration(migrations.Migration):
    dependencies = [("clinica", "0013_sessaofono")]
    operations = [migrations.RunPython(instalar, remover)]
