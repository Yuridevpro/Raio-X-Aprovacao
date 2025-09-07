# questoes/utils.py

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# =======================================================================
# PASSO 1: CORRIGIR A FUNÇÃO GENÉRICA
# Esta função agora terá a lógica de paginação correta e será a única
# fonte de verdade para a criação dos números de página.
# =======================================================================
def paginar_itens(request, queryset, items_per_page=15):
    """
    Função genérica para paginar qualquer queryset e gerar a lista de páginas correta.
    """
    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get('page', 1)

    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(paginator.num_pages if paginator.num_pages > 0 else 1)

    # Lógica de customização dos números de página (A VERSÃO CORRETA)
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
            
    return page_obj, page_numbers


# =======================================================================
# PASSO 2: REATORAR A FUNÇÃO ANTIGA
# Agora que temos uma função genérica perfeita, vamos fazer com que a
# função de filtrar questões a utilize, em vez de ter sua própria lógica.
# =======================================================================
def filtrar_e_paginar_questoes(request, base_queryset, items_per_page=15):
    """
    Centraliza a lógica de filtrar e agora USA a função genérica para paginar.
    """
    
    # 1. Lógica de Filtragem (permanece a mesma)
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

    # 2. Lógica de Paginação (AGORA USANDO A FUNÇÃO GENÉRICA)
    # Removemos todo o código de paginação duplicado daqui.
    questoes_paginadas, page_numbers = paginar_itens(request, lista_questoes, items_per_page)
    
    # 3. Montagem do Contexto de Retorno
    context = {
        'questoes': questoes_paginadas,
        'page_numbers': page_numbers, # Vem da nossa função genérica!
        'selected_disciplinas': [int(i) for i in disciplinas_ids if i.isdigit()],
        'selected_assuntos': [int(i) for i in assuntos_ids if i.isdigit()],
        'selected_bancas': [int(i) for i in bancas_ids if i.isdigit()],
        'selected_instituicoes': [int(i) for i in instituicoes_ids if i.isdigit()],
        'selected_anos': [int(a) for a in anos if a.isdigit()],
        'palavra_chave_buscada': palavra_chave,
    }
    
    return context