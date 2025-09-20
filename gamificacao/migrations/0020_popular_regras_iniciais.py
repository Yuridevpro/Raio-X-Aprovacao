# gamificacao/migrations/0020_popular_regras_iniciais.py

from django.db import migrations

def criar_regras_iniciais(apps, schema_editor):
    """
    Cria um conjunto de Regras de Recompensa padrão para popular o sistema.
    """
    RegraRecompensa = apps.get_model('gamificacao', 'RegraRecompensa')
    
    regras = [
        {
            "nome": "Top 3 do Ranking Semanal",
            "ativo": True,
            "gatilho": "RANKING_SEMANAL_TOP_N",
            "condicoes": {"top_n": 3},
            "xp_extra": 50
        },
        {
            "nome": "Top 3 do Ranking Mensal",
            "ativo": True,
            "gatilho": "RANKING_MENSAL_TOP_N",
            "condicoes": {"top_n": 3},
            "xp_extra": 150
        },
        {
            "nome": "Excelente Desempenho em Simulado",
            "ativo": True,
            "gatilho": "COMPLETAR_SIMULADO",
            "condicoes": {"min_acertos_percent": 80},
            "xp_extra": 75
        },
    ]

    for regra_data in regras:
        RegraRecompensa.objects.get_or_create(
            nome=regra_data["nome"],
            defaults=regra_data
        )

def remover_regras_iniciais(apps, schema_editor):
    """
    Remove as regras criadas, caso seja necessário reverter a migração.
    """
    RegraRecompensa = apps.get_model('gamificacao', 'RegraRecompensa')
    nomes_para_deletar = [
        "Top 3 do Ranking Semanal",
        "Top 3 do Ranking Mensal",
        "Excelente Desempenho em Simulado"
    ]
    RegraRecompensa.objects.filter(nome__in=nomes_para_deletar).delete()


class Migration(migrations.Migration):

    dependencies = [
        # Altere para o nome da migração anterior (provavelmente 0019)
        ('gamificacao', '0019_gamificationsettings_multiplicador_xp_simulado_and_more'), 
    ]

    operations = [
        # ESTA É A LINHA QUE ESTAVA FALTANDO!
        # Ela diz ao Django para executar as funções que você definiu.
        migrations.RunPython(criar_regras_iniciais, reverse_code=remover_regras_iniciais),
    ]