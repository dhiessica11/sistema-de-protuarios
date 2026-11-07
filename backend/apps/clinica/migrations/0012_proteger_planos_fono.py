from django.db import migrations


TABELAS = ("clinica_planofono", "clinica_itemplanofono")


def instalar(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for tabela in TABELAS:
        schema_editor.execute(
            f"CREATE TRIGGER preservar_fono BEFORE UPDATE OR DELETE ON {tabela} FOR EACH ROW EXECUTE FUNCTION clinica_fono_preservar()"
        )
    schema_editor.execute("""
        CREATE FUNCTION clinica_plano_item_valido() RETURNS trigger AS $$
        DECLARE paciente_plano uuid; paciente_revisao uuid; decisao_revisao varchar(12);
        BEGIN
            SELECT paciente_id INTO paciente_plano FROM clinica_planofono WHERE id = NEW.plano_id;
            SELECT a.paciente_id, r.decisao INTO paciente_revisao, decisao_revisao
              FROM clinica_revisaoobjetivofono r
              JOIN clinica_dificuldadefono d ON d.id = r.dificuldade_id
              JOIN clinica_avaliacaofono a ON a.id = d.avaliacao_id
             WHERE r.id = NEW.revisao_id;
            IF paciente_plano IS NULL OR paciente_revisao IS NULL OR
               paciente_plano IS DISTINCT FROM paciente_revisao OR decisao_revisao <> 'aprovado' THEN
                RAISE EXCEPTION 'Item deve usar revisão aprovada do mesmo paciente';
            END IF;
            RETURN NEW;
        END; $$ LANGUAGE plpgsql
    """)
    schema_editor.execute(
        "CREATE TRIGGER plano_item_validar BEFORE INSERT ON clinica_itemplanofono FOR EACH ROW EXECUTE FUNCTION clinica_plano_item_valido()"
    )


def remover(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP TRIGGER IF EXISTS plano_item_validar ON clinica_itemplanofono")
    schema_editor.execute("DROP FUNCTION IF EXISTS clinica_plano_item_valido()")
    for tabela in TABELAS:
        schema_editor.execute(f"DROP TRIGGER IF EXISTS preservar_fono ON {tabela}")


class Migration(migrations.Migration):
    dependencies = [("clinica", "0011_planofono_itemplanofono_and_more")]
    operations = [migrations.RunPython(instalar, remover)]
