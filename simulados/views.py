# simulados/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import models
from django.db.models import Exists, OuterRef, Count
from django.contrib import messages
from random import sample
import json
import markdown
from django.contrib.auth.models import User
from django.urls import reverse

from .models import Simulado, SessaoSimulado, RespostaSimulado, StatusSimulado, NivelDificuldade
from questoes.models import Questao, Disciplina, Banca, Instituicao, Assunto
from .forms import SimuladoAvancadoForm
from questoes.utils import paginar_itens
from django.views.decorators.cache import never_cache
from collections import defaultdict
from django.db.models import Prefetch

# simulados/views.py

@login_required
def listar_simulados(request):
    """
    Página VITRINE: Exibe os simulados oficiais mais populares (que não estão arquivados)
    e os simulados pessoais do usuário (com paginação).
    """
    usuario = request.user
    sessao_em_andamento = SessaoSimulado.objects.filter(simulado=OuterRef('pk'), usuario=usuario, finalizado=False)

    simulados_oficiais = Simulado.objects.filter(
        is_oficial=True
    ).exclude(
        status=StatusSimulado.ARQUIVADO
    ).annotate(
        num_sessoes=Count('sessaosimulado'),
        num_questoes=Count('questoes', distinct=True),
        sessao_ativa_id=models.Subquery(sessao_em_andamento.values('id')[:1])
    ).prefetch_related(
        Prefetch('sessaosimulado_set', 
                 queryset=SessaoSimulado.objects.filter(usuario=usuario, finalizado=True).order_by('-data_fim'), 
                 to_attr='sessoes_finalizadas_usuario'),
        Prefetch('questoes', queryset=Questao.objects.select_related('disciplina'), to_attr='questoes_com_disciplinas')
    ).order_by('-num_sessoes', '-data_criacao')[:8]

    # Processamento para obter as disciplinas únicas
    for simulado in simulados_oficiais:
        simulado.principais_disciplinas = []
        if hasattr(simulado, 'questoes_com_disciplinas'):
            disciplinas = defaultdict(int)
            for questao in simulado.questoes_com_disciplinas:
                if questao.disciplina:
                    disciplinas[questao.disciplina.nome] += 1
            simulado.principais_disciplinas = [item[0] for item in sorted(disciplinas.items(), key=lambda x: x[1], reverse=True)[:2]]

    simulados_pessoais_list = Simulado.objects.filter(
        criado_por=usuario, is_oficial=False
    ).annotate(
        num_questoes=Count('questoes'),
        sessao_ativa_id=models.Subquery(sessao_em_andamento.values('id')[:1]),
        sessao_concluida_id=models.Subquery(SessaoSimulado.objects.filter(simulado=OuterRef('pk'), usuario=usuario, finalizado=True).values('id')[:1])
    ).order_by('-data_criacao')
    
    page_obj, page_numbers, per_page = paginar_itens(request, simulados_pessoais_list, items_per_page=5)

    context = {
        'simulados_oficiais': simulados_oficiais,
        'simulados_pessoais': page_obj,
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'per_page': per_page,
    }
    
    return render(request, 'simulados/listar_simulados.html', context)


@login_required
def listar_simulados_oficiais(request):
    """
    Página BIBLIOTECA: Lista TODOS os simulados oficiais que não estão arquivados,
    com filtros, ordenação e paginação.
    """
    usuario = request.user
    base_queryset = Simulado.objects.filter(
        is_oficial=True
    ).exclude(
        status=StatusSimulado.ARQUIVADO
    )

    # --- Filtros ---
    filtro_disciplinas_str = request.GET.getlist('disciplina')
    filtro_bancas_str = request.GET.getlist('banca')
    filtro_instituicoes_str = request.GET.getlist('instituicao')
    filtro_dificuldade = request.GET.get('dificuldade')
    
    filtro_disciplinas = [int(i) for i in filtro_disciplinas_str if i.isdigit()]
    filtro_bancas = [int(i) for i in filtro_bancas_str if i.isdigit()]
    filtro_instituicoes = [int(i) for i in filtro_instituicoes_str if i.isdigit()]

    if filtro_disciplinas:
        base_queryset = base_queryset.filter(questoes__disciplina__id__in=filtro_disciplinas)
    if filtro_bancas:
        base_queryset = base_queryset.filter(questoes__banca__id__in=filtro_bancas)
    if filtro_instituicoes:
        base_queryset = base_queryset.filter(questoes__instituicao__id__in=filtro_instituicoes)
    if filtro_dificuldade:
        base_queryset = base_queryset.filter(dificuldade=filtro_dificuldade)

    # --- Ordenação ---
    sort_by = request.GET.get('sort_by', '-num_sessoes')
    sort_options = {
        '-num_sessoes': 'Mais Populares',
        '-data_criacao': 'Mais Recentes',
        'nome': 'Nome (A-Z)',
    }
    
    sessao_em_andamento = SessaoSimulado.objects.filter(simulado=OuterRef('pk'), usuario=usuario, finalizado=False)
    
    base_queryset = base_queryset.annotate(
        num_sessoes=Count('sessaosimulado'),
        num_questoes=Count('questoes', distinct=True),
        sessao_ativa_id=models.Subquery(sessao_em_andamento.values('id')[:1])
    ).prefetch_related(
        Prefetch('sessaosimulado_set', 
                 queryset=SessaoSimulado.objects.filter(usuario=usuario, finalizado=True).order_by('-data_fim'), 
                 to_attr='sessoes_finalizadas_usuario'),
        Prefetch('questoes', queryset=Questao.objects.select_related('disciplina'), to_attr='questoes_com_disciplinas')
    ).distinct()

    if sort_by in sort_options:
        base_queryset = base_queryset.order_by(sort_by)

    # --- Paginação ---
    per_page = request.GET.get('per_page', 9)
    page_obj, page_numbers, per_page = paginar_itens(request, base_queryset, items_per_page=per_page)
    
    # Adiciona as disciplinas principais a cada simulado paginado
    for simulado in page_obj.object_list:
        simulado.principais_disciplinas = []
        if hasattr(simulado, 'questoes_com_disciplinas'):
            disciplinas = defaultdict(int)
            for questao in simulado.questoes_com_disciplinas:
                if questao.disciplina:
                    disciplinas[questao.disciplina.nome] += 1
            simulado.principais_disciplinas = [item[0] for item in sorted(disciplinas.items(), key=lambda x: x[1], reverse=True)[:2]]

    # --- Contexto ---
    context = {
        'simulados': page_obj,
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'sort_by': sort_by,
        'sort_options': sort_options,
        
        'disciplinas': Disciplina.objects.all().order_by('nome'),
        'bancas': Banca.objects.all().order_by('nome'),
        'instituicoes': Instituicao.objects.all().order_by('nome'),
        'dificuldades': NivelDificuldade.choices,
        'assuntos_url': reverse('questoes:get_assuntos_por_disciplina'),
        
        'selected_disciplinas': filtro_disciplinas,
        'selected_bancas': filtro_bancas,
        'selected_instituicoes': filtro_instituicoes,
        'selected_dificuldade': filtro_dificuldade,
        'selected_assuntos_json': "[]",
    }

    return render(request, 'simulados/listar_simulados_oficiais.html', context)


@login_required
@require_POST # Garante que a view só pode ser acessada via método POST
def excluir_simulado(request, simulado_id):
    """
    Exclui um simulado que foi criado pelo usuário logado.
    """
    # A busca get_object_or_404 garante que o simulado existe e pertence ao usuário.
    # Se qualquer uma das condições falhar, um erro 404 será retornado.
    simulado = get_object_or_404(Simulado, id=simulado_id, criado_por=request.user)
    
    nome_simulado = simulado.nome
    simulado.delete()
    
    messages.success(request, f"O simulado '{nome_simulado}' foi excluído com sucesso.")
    return redirect('simulados:listar_simulados')
# ===========================================================
# FIM DA ADIÇÃO
# ===========================================================

@login_required
def iniciar_ou_continuar_sessao(request, simulado_id):
    simulado = get_object_or_404(Simulado, id=simulado_id)
    usuario = request.user

    sessao = SessaoSimulado.objects.filter(
        simulado=simulado, usuario=usuario, finalizado=False
    ).first()

    if not sessao:
        sessao = SessaoSimulado.objects.create(simulado=simulado, usuario=usuario)
    
    return redirect('simulados:realizar_simulado', sessao_id=sessao.id)


@login_required
def gerar_simulado_avancado(request):
    """
    Página de criação avançada de simulados, permitindo seleção
    granular de disciplinas e quantidade de questões.
    """
    if request.method == 'POST':
        form = SimuladoAvancadoForm(request.POST)
        if form.is_valid():
            nome = form.cleaned_data['nome']
            tempo_por_questao = form.cleaned_data.get('tempo_por_questao')
            if tempo_por_questao == 0:
                tempo_por_questao = None

            questoes_selecionadas_ids = []
            
            for key, qtd_str in request.POST.items():
                if key.startswith('disciplina-'):
                    try:
                        disciplina_id = int(key.split('-')[1])
                        qtd = int(qtd_str)

                        if qtd > 0:
                            # ===========================================================
                            # INÍCIO DA CORREÇÃO: Usando o manager padrão `objects`
                            # para buscar apenas questões ATIVAS.
                            # ===========================================================
                            ids_disponiveis = list(Questao.objects.filter(
                                disciplina_id=disciplina_id
                            ).values_list('id', flat=True))
                            # ===========================================================
                            # FIM DA CORREÇÃO
                            # ===========================================================

                            qtd_real = min(qtd, len(ids_disponiveis))
                            ids_sorteados = sample(ids_disponiveis, qtd_real)
                            questoes_selecionadas_ids.extend(ids_sorteados)

                    except (ValueError, IndexError):
                        continue

            if not questoes_selecionadas_ids or len(questoes_selecionadas_ids) < 10:
                messages.error(request, "O simulado deve ter no mínimo 10 questões. Por favor, ajuste as quantidades.")
                return redirect('simulados:gerar_simulado_usuario')

            simulado = Simulado.objects.create(
                nome=nome,
                tempo_por_questao=tempo_por_questao,
                criado_por=request.user,
                is_oficial=False
            )
            simulado.questoes.set(questoes_selecionadas_ids)

            messages.success(request, f"Simulado '{simulado.nome}' gerado com sucesso!")
            return redirect('simulados:listar_simulados')
    else:
        form = SimuladoAvancadoForm()

    # =======================================================================
    # INÍCIO DA CORREÇÃO: Filtrando apenas questões ativas na contagem inicial.
    # `Questao.objects` já faz isso por padrão por causa do nosso custom manager.
    # =======================================================================
    context = {
        'form': form,
        'disciplinas': Disciplina.objects.annotate(
            num_questoes=Count('questao', filter=models.Q(questao__is_deleted=False))
        ).filter(num_questoes__gt=0).order_by('nome')
    }
    # =======================================================================
    # FIM DA CORREÇÃO
    # =======================================================================
    return render(request, 'simulados/gerar_simulado_avancado.html', context)


@login_required
def api_contar_questoes_por_disciplina(request):
    """
    API que retorna a contagem de questões ATIVAS para uma lista de IDs de disciplina.
    """
    disciplina_ids_str = request.GET.get('ids', '')
    if not disciplina_ids_str:
        return JsonResponse({'status': 'error', 'message': 'Nenhum ID fornecido'}, status=400)
    
    disciplina_ids = [int(id) for id in disciplina_ids_str.split(',') if id.isdigit()]
    
    # =======================================================================
    # INÍCIO DA CORREÇÃO: Adicionando o filtro para contar apenas questões ativas.
    # =======================================================================
    contagens = Disciplina.objects.filter(id__in=disciplina_ids).annotate(
        num_questoes=Count('questao', filter=models.Q(questao__is_deleted=False))
    ).values('id', 'num_questoes')
    # =======================================================================
    # FIM DA CORREÇÃO
    # =======================================================================
    
    data = {item['id']: item['num_questoes'] for item in contagens}
    
    return JsonResponse({'status': 'success', 'data': data})


@login_required
def realizar_simulado(request, sessao_id):
    sessao = get_object_or_404(SessaoSimulado.objects.select_related('simulado'), id=sessao_id, usuario=request.user)
    if sessao.finalizado:
        return redirect('simulados:resultado_simulado', sessao_id=sessao.id)

    questoes = sessao.simulado.questoes.select_related('disciplina', 'assunto', 'banca').order_by('id')
    total_questoes = questoes.count()
    
    respostas_dadas = RespostaSimulado.objects.filter(sessao=sessao).values('questao_id', 'alternativa_selecionada')
    mapa_respostas = {r['questao_id']: r['alternativa_selecionada'] for r in respostas_dadas}

    questoes_data = []
    for i, questao in enumerate(questoes, 1):
        # ===========================================================
        # INÍCIO DA MODIFICAÇÃO
        # ===========================================================
        banca_nome = "Inédita" if questao.is_inedita else (questao.banca.nome if questao.banca else '')
        # ===========================================================
        # FIM DA MODIFICAÇÃO
        # ===========================================================

        questoes_data.append({
            'numero': i,
            'id': questao.id,
            'enunciado_html': markdown.markdown(questao.enunciado),
            'alternativas': questao.get_alternativas_dict(),
            'resposta_usuario': mapa_respostas.get(questao.id),
            'disciplina': questao.disciplina.nome,
            # ===========================================================
            # INÍCIO DA MODIFICAÇÃO
            # ===========================================================
            'banca': banca_nome,
            # ===========================================================
            # FIM DA MODIFICAÇÃO
            # ===========================================================
            'ano': questao.ano or '',
        })

    duracao_total_minutos = total_questoes * 2
    tempo_decorrido = timezone.now() - sessao.data_inicio
    tempo_restante_segundos = (duracao_total_minutos * 60) - tempo_decorrido.total_seconds()

    context = {
        'sessao': sessao,
        'questoes_data': json.dumps(questoes_data),
        'total_questoes': total_questoes,
        'tempo_restante_segundos': tempo_restante_segundos,
    }
    
    return render(request, 'simulados/realizar_simulado.html', context)

@login_required
@require_POST
def registrar_resposta_simulado(request, sessao_id):
    sessao = get_object_or_404(SessaoSimulado, id=sessao_id, usuario=request.user)
    if sessao.finalizado:
        return JsonResponse({'status': 'error', 'message': 'Este simulado já foi finalizado.'}, status=403)
        
    data = json.loads(request.body)
    questao_id = data.get('questao_id')
    alternativa = data.get('alternativa')
    
    RespostaSimulado.objects.update_or_create(
        sessao=sessao,
        questao_id=questao_id,
        defaults={'alternativa_selecionada': alternativa}
    )
    return JsonResponse({'status': 'success'})

@login_required
def finalizar_simulado(request, sessao_id):
    sessao = get_object_or_404(SessaoSimulado, id=sessao_id, usuario=request.user)
    if sessao.finalizado:
        return redirect('simulados:resultado_simulado', sessao_id=sessao.id)

    respostas_para_corrigir = RespostaSimulado.objects.filter(sessao=sessao).select_related('questao')
    for resposta in respostas_para_corrigir:
        if resposta.alternativa_selecionada:
            resposta.foi_correta = (resposta.alternativa_selecionada == resposta.questao.gabarito)
        else:
            resposta.foi_correta = False
        resposta.save()
    
    sessao.finalizar_sessao()
    return redirect('simulados:resultado_simulado', sessao_id=sessao.id)

def formatar_tempo_gasto(total_seconds):
    if total_seconds < 0:
        total_seconds = 0
    
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours} hora{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minuto{'s' if minutes > 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} segundo{'s' if seconds > 1 else ''}")
        
    return ", ".join(parts)

@login_required
def resultado_simulado(request, sessao_id):
    sessao = get_object_or_404(SessaoSimulado, id=sessao_id, usuario=request.user)

    if not sessao.finalizado:
        messages.warning(request, "Você precisa finalizar o simulado para ver os resultados.")
        return redirect('simulados:realizar_simulado', sessao_id=sessao.id)

    # =======================================================================
    # INÍCIO DA CORREÇÃO: Lógica do Dashboard de Resultados
    # =======================================================================
    respostas_usuario = sessao.respostas.select_related('questao__disciplina', 'questao__banca').order_by('questao__id')
    questoes_simulado = sessao.simulado.questoes.all()
    
    # --- Métricas Principais ---
    total_questoes = questoes_simulado.count()
    total_acertos = respostas_usuario.filter(foi_correta=True).count()
    total_respondidas = respostas_usuario.exclude(alternativa_selecionada__isnull=True).count()
    total_erros = total_respondidas - total_acertos
    total_em_branco = total_questoes - total_respondidas
    percentual_acerto = (total_acertos / total_questoes * 100) if total_questoes > 0 else 0

    # --- Métricas de Tempo ---
    tempo_gasto_td = sessao.data_fim - sessao.data_inicio
    tempo_gasto_segundos = tempo_gasto_td.total_seconds()
    tempo_gasto_formatado = formatar_tempo_gasto(tempo_gasto_segundos)
    
    tempo_em_minutos = tempo_gasto_segundos / 60
    acertos_por_minuto = (total_acertos / tempo_em_minutos) if tempo_em_minutos > 0 else 0

    # --- Desempenho por Disciplina ---
    desempenho_disciplina = defaultdict(lambda: {'acertos': 0, 'total': 0})
    for resposta in respostas_usuario:
        disciplina = resposta.questao.disciplina.nome
        desempenho_disciplina[disciplina]['total'] += 1
        if resposta.foi_correta:
            desempenho_disciplina[disciplina]['acertos'] += 1
    
    desempenho_final = [
        {
            'disciplina': disc,
            'acertos': data['acertos'],
            'total': data['total'],
            'percentual': (data['acertos'] / data['total'] * 100) if data['total'] > 0 else 0
        }
        for disc, data in desempenho_disciplina.items()
    ]
    
    # --- Revisão Detalhada (lógica existente) ---
    mapa_respostas = {r.questao_id: r for r in respostas_usuario}
    revisao_detalhada = []
    for i, questao in enumerate(questoes_simulado.order_by('id'), 1):
        resposta = mapa_respostas.get(questao.id)
        revisao_detalhada.append({
            'numero': i, 'questao': questao,
            'resposta_usuario': resposta.alternativa_selecionada if resposta else None,
            'foi_correta': resposta.foi_correta if resposta else False,
            'explicacao_html': markdown.markdown(questao.explicacao) if questao.explicacao else ""
        })
    
    context = {
        'sessao': sessao,
        'total_questoes': total_questoes,
        'total_acertos': total_acertos,
        'total_erros': total_erros,
        'total_em_branco': total_em_branco,
        'percentual_acerto': round(percentual_acerto, 2),
        'tempo_gasto_formatado': tempo_gasto_formatado,
        'acertos_por_minuto': round(acertos_por_minuto, 2),
        'desempenho_disciplina': desempenho_final,
        'revisao_detalhada': revisao_detalhada,
    }
    # =======================================================================
    # FIM DA CORREÇÃO
    # =======================================================================

    return render(request, 'simulados/resultado_simulado.html', context)

@login_required
def historico_simulado(request, simulado_id):
    """
    Lista, com paginação, todo o histórico de sessões finalizadas
    de um usuário para um simulado específico.
    """
    simulado = get_object_or_404(Simulado, id=simulado_id)
    
    sessoes_list = SessaoSimulado.objects.filter(
        simulado=simulado,
        usuario=request.user,
        finalizado=True
    ).annotate(
        num_acertos=Count('respostas', filter=models.Q(respostas__foi_correta=True)),
        num_questoes=Count('simulado__questoes')
    ).order_by('-data_fim')

    page_obj, page_numbers, per_page = paginar_itens(request, sessoes_list, items_per_page=10)

    context = {
        'simulado': simulado,
        'sessoes': page_obj,
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
    }
    return render(request, 'simulados/historico_simulado.html', context)


@login_required
@require_POST
def excluir_sessao_simulado(request, sessao_id):
    """ Exclui uma única tentativa (sessão) do histórico do usuário. """
    sessao = get_object_or_404(SessaoSimulado, id=sessao_id, usuario=request.user)
    simulado_id = sessao.simulado.id
    sessao.delete()
    messages.success(request, "Tentativa de simulado excluída com sucesso do seu histórico.")
    return redirect('simulados:historico_simulado', simulado_id=simulado_id)


@login_required
@require_POST
def limpar_historico_simulado(request, simulado_id):
    """ Exclui TODAS as tentativas (sessões) de um simulado do histórico do usuário. """
    simulado = get_object_or_404(Simulado, id=simulado_id)
    sessoes = SessaoSimulado.objects.filter(simulado=simulado, usuario=request.user, finalizado=True)
    
    count = sessoes.count()
    if count > 0:
        sessoes.delete()
        messages.success(request, f"{count} registro(s) do seu histórico para este simulado foram limpos com sucesso.")
    else:
        messages.info(request, "Não havia histórico para ser limpo.")
        
    return redirect('simulados:listar_simulados')
# =======================================================================
# FIM DA ADIÇÃO
# =======================================================================


