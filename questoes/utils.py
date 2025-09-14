# questoes/utils.py

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

def paginar_itens(request, queryset, items_per_page=15):
    """
    Função genérica para paginar qualquer queryset e gerar a lista de páginas correta.
    Agora lê a quantidade de itens por página da URL.
    """
    try:
        per_page = int(request.GET.get('per_page', items_per_page))
        if per_page not in [10, 20, 50]:
            per_page = items_per_page
    except (ValueError, TypeError):
        per_page = items_per_page

    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page', 1)

    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(paginator.num_pages if paginator.num_pages > 0 else 1)

    page_numbers = []
    current_page = page_obj.number
    total_pages = paginator.num_pages

    if total_pages <= 7:
        page_numbers = list(range(1, total_pages + 1))
    else:
        if current_page <= 4:
            page_numbers = list(range(1, 6)) + ['...', total_pages]
        elif current_page >= total_pages - 3:
            page_numbers = [1, '...'] + list(range(total_pages - 4, total_pages + 1))
        else:
            page_numbers = [1, '...', current_page - 1, current_page, current_page + 1, '...', total_pages]
            
    return page_obj, page_numbers, per_page


def filtrar_e_paginar_questoes(request, base_queryset, items_per_page=15):
    """
    Centraliza a lógica de filtrar e agora USA a função genérica para paginar.
    (ESTA FUNÇÃO PERMANECE INTACTA)
    """
    palavra_chave = request.GET.get('palavra_chave', '').strip()
    disciplinas_ids = request.GET.getlist('disciplina')
    assuntos_ids = request.GET.getlist('assunto')
    bancas_ids = request.GET.getlist('banca')
    instituicoes_ids = request.GET.getlist('instituicao')
    anos = request.GET.getlist('ano')
    
    lista_questoes = base_queryset

    if disciplinas_ids:
        lista_questoes = lista_questoes.filter(disciplina_id__in=disciplinas_ids)
    if assuntos_ids:
        lista_questoes = lista_questoes.filter(assunto_id__in=assuntos_ids)
    if bancas_ids:
        lista_questoes = lista_questoes.filter(banca_id__in=bancas_ids)
    if instituicoes_ids:
        lista_questoes = lista_questoes.filter(instituicao_id__in=instituicoes_ids)
    if anos:
        lista_questoes = lista_questoes.filter(ano__in=anos)
    
    if palavra_chave:
        if palavra_chave.upper().startswith('Q') and palavra_chave[1:].isdigit():
            lista_questoes = lista_questoes.filter(codigo__iexact=palavra_chave)
        else:
            lista_questoes = lista_questoes.filter(enunciado__icontains=palavra_chave)

    questoes_paginadas, page_numbers, per_page = paginar_itens(request, lista_questoes, items_per_page)
    
    context = {
        'questoes': questoes_paginadas,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'selected_disciplinas': [int(i) for i in disciplinas_ids if i.isdigit()],
        'selected_assuntos': [int(i) for i in assuntos_ids if i.isdigit()],
        'selected_bancas': [int(i) for i in bancas_ids if i.isdigit()],
        'selected_instituicoes': [int(i) for i in instituicoes_ids if i.isdigit()],
        'selected_anos': [int(a) for a in anos if a.isdigit()],
        'palavra_chave_buscada': palavra_chave,
    }
    
    return context

# =======================================================================
# INÍCIO DA ADIÇÃO: Nova função de filtro específica para a lixeira
# =======================================================================
def filtrar_e_paginar_lixeira(request, base_queryset, items_per_page=20):
    """
    Função de filtro dedicada para a página da lixeira.
    Usa .get() para filtros de seleção única, correspondendo ao novo template de filtros.
    """
    termo_busca = request.GET.get('q', '').strip()
    disciplina_id = request.GET.get('disciplina')
    banca_id = request.GET.get('banca')
    instituicao_id = request.GET.get('instituicao')
    ano_selecionado = request.GET.get('ano')
    
    queryset_filtrado = base_queryset

    if termo_busca:
        queryset_filtrado = queryset_filtrado.filter(
            Q(enunciado__icontains=termo_busca) | Q(codigo__iexact=termo_busca)
        )
    if disciplina_id:
        queryset_filtrado = queryset_filtrado.filter(disciplina_id=disciplina_id)
    if banca_id:
        queryset_filtrado = queryset_filtrado.filter(banca_id=banca_id)
    if instituicao_id:
        queryset_filtrado = queryset_filtrado.filter(instituicao_id=instituicao_id)
    if ano_selecionado:
        queryset_filtrado = queryset_filtrado.filter(ano=ano_selecionado)

    questoes_paginadas, page_numbers, per_page = paginar_itens(request, queryset_filtrado, items_per_page)
    
    context = {
        'questoes': questoes_paginadas,
        'paginated_object': questoes_paginadas,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'active_filters': request.GET, # Passa todos os filtros para preencher o formulário de filtros
    }
    
    return context
# =======================================================================
# FIM DA ADIÇÃO
# =======================================================================

def filtrar_e_paginar_questoes_com_prefixo(request, base_queryset, items_per_page=15, prefix=''):
    """
    Versão da função `filtrar_e_paginar_questoes` que suporta um prefixo nos
    parâmetros GET, permitindo o uso em páginas complexas como um componente.
    Esta versão lida com SELEÇÃO MÚLTIPLA.
    """
    # 1. Coleta dos filtros usando o prefixo e .getlist() para seleção múltipla
    palavra_chave = request.GET.get(f'{prefix}palavra_chave', '').strip()
    disciplinas_ids = request.GET.getlist(f'{prefix}disciplina')
    assuntos_ids = request.GET.getlist(f'{prefix}assunto')
    bancas_ids = request.GET.getlist(f'{prefix}banca')
    instituicoes_ids = request.GET.getlist(f'{prefix}instituicao')
    anos = request.GET.getlist(f'{prefix}ano')
    
    # =======================================================================
    # INÍCIO DA CORREÇÃO: Filtrar IDs vazios antes da consulta
    # =======================================================================
    # Remove strings vazias das listas de IDs, que causam o ValueError.
    disciplinas_ids = [val for val in disciplinas_ids if val]
    assuntos_ids = [val for val in assuntos_ids if val]
    bancas_ids = [val for val in bancas_ids if val]
    instituicoes_ids = [val for val in instituicoes_ids if val]
    anos = [val for val in anos if val]
    # =======================================================================
    # FIM DA CORREÇÃO
    # =======================================================================

    # 2. Aplicação dos filtros no queryset
    lista_questoes = base_queryset
    if disciplinas_ids:
        lista_questoes = lista_questoes.filter(disciplina_id__in=disciplinas_ids)
    if assuntos_ids:
        lista_questoes = lista_questoes.filter(assunto_id__in=assuntos_ids)
    if bancas_ids:
        lista_questoes = lista_questoes.filter(banca_id__in=bancas_ids)
    if instituicoes_ids:
        lista_questoes = lista_questoes.filter(instituicao_id__in=instituicoes_ids)
    if anos:
        lista_questoes = lista_questoes.filter(ano__in=anos)
    
    if palavra_chave:
        if palavra_chave.upper().startswith('Q') and palavra_chave[1:].isdigit():
            lista_questoes = lista_questoes.filter(codigo__iexact=palavra_chave)
        else:
            lista_questoes = lista_questoes.filter(enunciado__icontains=palavra_chave)

    # 3. Paginação usando o prefixo
    try:
        per_page = int(request.GET.get(f'{prefix}per_page', items_per_page))
        if per_page not in [10, 20, 50, 100]: per_page = items_per_page
    except (ValueError, TypeError):
        per_page = items_per_page
    
    paginator = Paginator(lista_questoes, per_page)
    page_number = request.GET.get(f'{prefix}page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(paginator.num_pages if paginator.num_pages > 0 else 1)

    # 4. Cálculo da lista de páginas (lógica genérica)
    page_numbers = []
    current_page = page_obj.number
    total_pages = paginator.num_pages
    if total_pages <= 7: page_numbers = list(range(1, total_pages + 1))
    else:
        if current_page <= 4: page_numbers = list(range(1, 6)) + ['...', total_pages]
        elif current_page >= total_pages - 3: page_numbers = [1, '...'] + list(range(total_pages - 4, total_pages + 1))
        else: page_numbers = [1, '...', current_page - 1, current_page, current_page + 1, '...', total_pages]
    
    # 5. Montagem do contexto de retorno, compatível com o template de filtro avançado
    context = {
        'questoes': page_obj,
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'prefix': prefix,
        # Variáveis necessárias para o template de filtro avançado saber o que está selecionado
        'selected_disciplinas': [int(i) for i in disciplinas_ids if i.isdigit()],
        'selected_assuntos': [int(i) for i in assuntos_ids if i.isdigit()],
        'selected_bancas': [int(i) for i in bancas_ids if i.isdigit()],
        'selected_instituicoes': [int(i) for i in instituicoes_ids if i.isdigit()],
        'selected_anos': [int(a) for a in anos if a.isdigit()],
        'palavra_chave_buscada': palavra_chave,
    }
    
    return context