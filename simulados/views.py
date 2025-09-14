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

from .models import Simulado, SessaoSimulado, RespostaSimulado
from questoes.models import Questao, Disciplina
from .forms import QuestaoFiltroForm
from questoes.utils import paginar_itens
from django.views.decorators.cache import never_cache


@login_required
def listar_simulados(request):
    """
    Lista, com paginação, todos os simulados OFICIAIS e os simulados
    PESSOAIS gerados pelo próprio usuário.
    """
    usuario = request.user
    
    # Sessões em andamento e finalizadas do usuário (lógica inalterada)
    sessao_em_andamento = SessaoSimulado.objects.filter(
        simulado=OuterRef('pk'), usuario=usuario, finalizado=False
    )
    sessao_finalizada = SessaoSimulado.objects.filter(
        simulado=OuterRef('pk'), usuario=usuario, finalizado=True
    )

    # =======================================================================
    # INÍCIO DA MODIFICAÇÃO: Usando 'is_oficial' para o filtro
    # =======================================================================
    # A nova lógica busca:
    # 1. Todos os simulados marcados como 'is_oficial=True'.
    # 2. OU todos os simulados criados pelo próprio usuário (que por padrão são 'is_oficial=False').
    simulados_list = Simulado.objects.filter(
        models.Q(is_oficial=True) | models.Q(criado_por=usuario)
    ).annotate(
        num_questoes=Count('questoes'),
        sessao_ativa_id=models.Subquery(sessao_em_andamento.values('id')[:1]),
        sessao_concluida_id=models.Subquery(sessao_finalizada.values('id')[:1])
    ).order_by('-data_criacao').distinct() # .distinct() para evitar duplicatas
    # =======================================================================
    # FIM DA MODIFICAÇÃO
    # =======================================================================

    # Paginação (lógica inalterada)
    page_obj, page_numbers, per_page = paginar_itens(request, simulados_list, items_per_page=6)
    
    context = {
        'simulados': page_obj,
        'paginated_object': page_obj,
        'page_numbers': page_numbers,
        'per_page': per_page,
        'sort_by': None,
        'sort_options': {},
    }
    
    return render(request, 'simulados/listar_simulados.html', context)
# ===========================================================
# INÍCIO DA ADIÇÃO: Nova view para excluir simulado
# ===========================================================
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
def gerar_simulado_usuario(request):
    if request.method == 'POST':
        form = QuestaoFiltroForm(request.POST)
        if form.is_valid():
            disciplina = form.cleaned_data['disciplina']
            num_questoes = int(form.cleaned_data['num_questoes'])
            questoes_ids = list(Questao.objects.filter(disciplina=disciplina).values_list('id', flat=True))
            
            if len(questoes_ids) < num_questoes:
                messages.warning(request, f"Encontramos apenas {len(questoes_ids)} questões para os filtros selecionados. O simulado será criado com este número.")
                num_questoes = len(questoes_ids)

            if num_questoes == 0:
                messages.error(request, "Nenhuma questão encontrada para os filtros selecionados.")
                return redirect('simulados:gerar_simulado_usuario')
                
            ids_selecionados = sample(questoes_ids, num_questoes)
            questoes_selecionadas = Questao.objects.filter(id__in=ids_selecionados)

            # Cria o simulado, mas NÃO cria a sessão ainda
            simulado = Simulado.objects.create(
                nome=f"Simulado de {disciplina.nome} - {timezone.now().strftime('%d/%m/%Y %H:%M')}",
                criado_por=request.user,
                # ===========================================================
                # INÍCIO DA MODIFICAÇÃO: Garante que o simulado não é oficial
                # ===========================================================
                is_oficial=False
                # ===========================================================
                # FIM DA MODIFICAÇÃO
                # ===========================================================
            )
            simulado.questoes.set(questoes_selecionadas)

            messages.success(request, f"Simulado '{simulado.nome}' gerado com sucesso! Ele aparecerá na lista abaixo.")

            # Redireciona para a lista de simulados
            return redirect('simulados:listar_simulados')
    else:
        form = QuestaoFiltroForm()

    context = {
        'form': form
    }
    return render(request, 'simulados/gerar_simulado_usuario.html', context)

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

    # Otimiza a query para buscar tudo de uma vez
    respostas_usuario = sessao.respostas.select_related('questao__disciplina', 'questao__banca').order_by('questao__id')
    
    # Busca todas as questões do simulado para garantir a contagem correta
    questoes_simulado = sessao.simulado.questoes.all()
    
    total_questoes = questoes_simulado.count()
    total_acertos = respostas_usuario.filter(foi_correta=True).count()
    total_respondidas = respostas_usuario.exclude(alternativa_selecionada__isnull=True).count()
    total_erros = total_respondidas - total_acertos
    total_em_branco = total_questoes - total_respondidas
    
    percentual_acerto = (total_acertos / total_questoes * 100) if total_questoes > 0 else 0
    
    tempo_gasto_td = sessao.data_fim - sessao.data_inicio
    tempo_gasto_formatado = formatar_tempo_gasto(tempo_gasto_td.total_seconds())

    mapa_respostas = {r.questao_id: r for r in respostas_usuario}
    revisao_detalhada = []
    for i, questao in enumerate(questoes_simulado.order_by('id'), 1):
        resposta = mapa_respostas.get(questao.id)
        revisao_detalhada.append({
            'numero': i,
            'questao': questao,
            'resposta_usuario': resposta.alternativa_selecionada if resposta else None,
            'foi_correta': resposta.foi_correta if resposta else False,
            # ===========================================================
            # ADIÇÃO: Renderiza a explicação em Markdown para HTML
            # ===========================================================
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
        'revisao_detalhada': revisao_detalhada,
    }

    return render(request, 'simulados/resultado_simulado.html', context)