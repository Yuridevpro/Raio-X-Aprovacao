# gamificacao/views.py (ARQUIVO COMPLETO)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from usuarios.models import UserProfile
from django.db.models import Count, Q, F, Window
from django.db.models.functions import Rank
from questoes.utils import paginar_itens # Reutilizando a função de paginação do app 'questoes'
from .services import verificar_e_gerar_rankings # <-- NOVO IMPORT
from .models import RankingSemanal, RankingMensal
from django.utils import timezone
from datetime import date, timedelta


@login_required
def ranking(request):
    """
    Exibe a página de ranking dos usuários, com base em critérios de desempenho
    como total de acertos e sequência de prática (streak).

    Esta view é otimizada para performance, realizando todos os cálculos
    e a ordenação diretamente no banco de dados.
    
    """
    verificar_e_gerar_rankings()

    periodo = request.GET.get('periodo', 'geral')
    hoje = date.today()
    
    ranking_list = UserProfile.objects.none()
    titulo_ranking = "Ranking Geral"
    
    
    # 1. Obter o parâmetro de ordenação da URL. O padrão é 'acertos'.
    sort_by = request.GET.get('sort_by', 'acertos')

    # 2. Construir o queryset base, que será a fonte para o ranking.
    #    - Filtra para incluir apenas usuários ativos que não são da equipe de gestão.
    #    - `select_related('streak_data')` otimiza a query, usando um JOIN para buscar
    #      os dados de streak na mesma consulta, evitando o problema N+1.
    base_queryset = UserProfile.objects.filter(
        user__is_active=True,
        user__is_staff=False
    ).select_related(
        'streak_data'
    ).annotate(
        # `annotate` adiciona campos calculados a cada objeto do queryset.
        # - `total_respostas`: Conta todas as respostas associadas ao usuário.
        total_respostas=Count('user__respostausuario'),
        # - `total_acertos`: Conta apenas as respostas onde 'foi_correta' é True.
        total_acertos=Count('user__respostausuario', filter=Q(user__respostausuario__foi_correta=True))
    ).filter(
        # Exibe no ranking apenas usuários que já responderam pelo menos uma questão.
        total_respostas__gt=0
    )

    # 3. Definir as opções de ordenação e o critério a ser usado.
    #    A ordenação secundária serve como critério de desempate.
    sort_options = {
        'acertos': ('-total_acertos', '-streak_data__current_streak'),
        'streak': ('-streak_data__current_streak', '-total_acertos'),
        'respostas': ('-total_respostas', '-total_acertos'),
    }
    
    # Seleciona a tupla de ordenação. Se o `sort_by` for inválido, usa o padrão 'acertos'.
    ordenacao = sort_options.get(sort_by, sort_options['acertos'])
    
    # 4. Anotar a posição (rank) de cada usuário.
    #    - `Window(expression=Rank(), order_by=...)` é uma função de janela do SQL
    #      que calcula a posição de cada linha com base em uma ordenação específica.
    #    - É crucial que a ordenação aqui seja a mesma do `.order_by()` final.
    queryset_ranqueado = base_queryset.annotate(
        rank=Window(
            expression=Rank(),
            order_by=[F(field[1:]).desc() if field.startswith('-') else F(field).asc() for field in ordenacao]
        )
    ).order_by(*ordenacao)

    # 5. Encontrar os dados do usuário logado no ranking para o card de destaque.
    posicao_usuario_logado = queryset_ranqueado.filter(user=request.user).first()

    # 6. Paginar a lista de resultados, exibindo 25 usuários por página.
    page_obj, page_numbers, per_page = paginar_itens(request, queryset_ranqueado, 25)

    # 7. Montar o contexto para ser enviado ao template.
    context = {
        'ranking_list': page_obj,
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'sort_by': sort_by,
        'posicao_usuario_logado': posicao_usuario_logado,
    }
    
    return render(request, 'gamificacao/ranking.html', context)