# desempenho/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from pratica.models import RespostaUsuario
# Precisamos de todos os modelos para os filtros
from questoes.models import Disciplina, Assunto, Banca, Instituicao
import json

@login_required
def dashboard(request):
    usuario = request.user

    # --- 1. CAPTURAR TODOS OS PARÂMETROS DE FILTRO ---
    periodo = request.GET.get('periodo', 'geral')
    disciplina_id = request.GET.get('disciplina')
    assunto_id = request.GET.get('assunto')
    banca_id = request.GET.get('banca')
    instituicao_id = request.GET.get('instituicao')

    # --- 2. CONSTRUIR O QUERYSET BASE DINAMICAMENTE ---
    respostas_base = RespostaUsuario.objects.filter(usuario=usuario)

    # Filtro de Período (igual ao anterior)
    now = timezone.now()
    start_date = None
    if periodo == 'hoje':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == 'semana':
        start_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == 'mes':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif periodo == 'ano':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    if start_date:
        respostas_base = respostas_base.filter(data_resposta__gte=start_date)

    # Filtros de Conteúdo
    if disciplina_id:
        respostas_base = respostas_base.filter(questao__disciplina_id=disciplina_id)
    if assunto_id:
        respostas_base = respostas_base.filter(questao__assunto_id=assunto_id)
    if banca_id:
        respostas_base = respostas_base.filter(questao__banca_id=banca_id)
    if instituicao_id:
        respostas_base = respostas_base.filter(questao__instituicao_id=instituicao_id)

    # --- 3. CALCULAR ESTATÍSTICAS GERAIS (COM BASE NOS FILTROS) ---
    total_respondidas = respostas_base.count()
    total_acertos = respostas_base.filter(foi_correta=True).count()
    total_erros = total_respondidas - total_acertos
    percentual_acerto_geral = (total_acertos / total_respondidas * 100) if total_respondidas > 0 else 0

    # --- 4. PREPARAR DADOS PARA OS GRÁFICOS E TABELAS ---

    # Desempenho por Banca (sempre relevante)
    desempenho_banca = Banca.objects.filter(
        questao__respostausuario__in=respostas_base
    ).annotate(
        total=Count('questao', filter=Q(questao__respostausuario__in=respostas_base)),
        acertos=Count('questao', filter=Q(questao__respostausuario__in=respostas_base, questao__respostausuario__foi_correta=True))
    ).filter(total__gt=0).order_by('-total')

    # Desempenho por Disciplina OU Assunto (Interface Dinâmica)
    desempenho_principal = []
    if disciplina_id:
        # Se uma disciplina foi selecionada, detalhamos por Assunto
        desempenho_principal = Assunto.objects.filter(
            questao__respostausuario__in=respostas_base
        ).annotate(
            total=Count('questao', filter=Q(questao__respostausuario__in=respostas_base)),
            acertos=Count('questao', filter=Q(questao__respostausuario__in=respostas_base, questao__respostausuario__foi_correta=True))
        ).filter(total__gt=0).order_by('-total')
    else:
        # Se nenhuma disciplina foi selecionada, mostramos o geral por Disciplina
        desempenho_principal = Disciplina.objects.filter(
            questao__respostausuario__in=respostas_base
        ).annotate(
            total=Count('questao', filter=Q(questao__respostausuario__in=respostas_base)),
            acertos=Count('questao', filter=Q(questao__respostausuario__in=respostas_base, questao__respostausuario__foi_correta=True))
        ).filter(total__gt=0).order_by('-total')
    
    for item in desempenho_principal:
        item.percentual_acerto = (item.acertos / item.total * 100) if item.total > 0 else 0

    # --- 5. PREPARAR DADOS PARA OS DROPDOWNS DE FILTRO ---
    disciplinas_para_filtro = Disciplina.objects.filter(questao__respostausuario__usuario=usuario).distinct().order_by('nome')
    bancas_para_filtro = Banca.objects.filter(questao__respostausuario__usuario=usuario).distinct().order_by('nome')
    instituicoes_para_filtro = Instituicao.objects.filter(questao__respostausuario__usuario=usuario).distinct().order_by('nome')
    
    assuntos_para_filtro = None
    if disciplina_id:
        assuntos_para_filtro = Assunto.objects.filter(disciplina_id=disciplina_id).order_by('nome')

    # Títulos para a UI
    periodo_titulos = {'geral': 'Todo o Período', 'hoje': 'Hoje', 'semana': 'Esta Semana', 'mes': 'Este Mês', 'ano': 'Este Ano'}
    periodo_titulo_selecionado = periodo_titulos.get(periodo, 'Todo o Período')

    context = {
        # Estatísticas
        'total_respondidas': total_respondidas,
        'total_acertos': total_acertos,
        'total_erros': total_erros,
        'percentual_acerto_geral': round(percentual_acerto_geral, 2),
        
        # Dados para tabelas e gráficos
        'desempenho_principal': desempenho_principal,
        'desempenho_banca': desempenho_banca,
        
        # Dados para os gráficos (JSON)
        'labels_banca': json.dumps([b.nome for b in desempenho_banca]),
        'data_acertos_banca': json.dumps([b.acertos for b in desempenho_banca]),
        
        # Filtros Selecionados (para manter o estado na UI)
        'periodo_selecionado': periodo,
        'periodo_titulo_selecionado': periodo_titulo_selecionado,
        'disciplina_selecionada': disciplina_id,
        'assunto_selecionado': assunto_id,
        'banca_selecionada': banca_id,
        'instituicao_selecionada': instituicao_id,
        
        # Opções para os dropdowns de filtro
        'disciplinas_para_filtro': disciplinas_para_filtro,
        'assuntos_para_filtro': assuntos_para_filtro,
        'bancas_para_filtro': bancas_para_filtro,
        'instituicoes_para_filtro': instituicoes_para_filtro,
    }

    return render(request, 'desempenho/dashboard.html', context)