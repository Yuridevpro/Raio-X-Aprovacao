# gestao/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from pratica.models import Notificacao # Importe o modelo de notificação
from django.utils import timezone
from usuarios.views import enviar_email_com_template # Importe a função de e-mail

# Modelos e Forms
from questoes.models import Questao, Disciplina, Banca, Instituicao, Assunto
from questoes.forms import GestaoQuestaoForm, EntidadeSimplesForm, AssuntoForm
from django.urls import reverse # <-- IMPORTAÇÃO NECESSÁRIA PARA A CORREÇÃO
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from questoes.utils import paginar_itens # Importe a NOVA função genérica
from django.db.models import Q, Count, OuterRef, Subquery # <-- LINHA CHAVE
from datetime import timedelta
import markdown # <--- ADICIONE ESTA LINHA
import json # <--- ADICIONE ESTA LINHA





# =======================================================================
# IMPORTAÇÃO DA NOSSA NOVA FUNÇÃO CENTRALIZADA
# =======================================================================
from questoes.utils import filtrar_e_paginar_questoes


def is_staff_member(user):
    return user.is_staff

@user_passes_test(is_staff_member)
@login_required
def dashboard_gestao(request):
    total_questoes = Questao.objects.count()
    context = {
        'total_questoes': total_questoes
    }
    return render(request, 'gestao/dashboard.html', context)

@user_passes_test(is_staff_member)
@login_required
def listar_questoes_gestao(request):
    """
    View para listar questões no painel de gestão.
    Agora utiliza a função centralizada para filtros e paginação.
    """
    # 1. Define o queryset base de questões para esta view.
    base_queryset = Questao.objects.select_related(
        'disciplina', 'assunto', 'banca'
    ).all().order_by('-id')

    # 2. Chama a função central para fazer todo o trabalho pesado de filtrar e paginar.
    context = filtrar_e_paginar_questoes(request, base_queryset, items_per_page=20)

    # 3. Adiciona ao contexto apenas as variáveis que são específicas desta página de gestão
    #    (como os dados para popular os modais e os dropdowns de filtro).
    context.update({
        'disciplinas_para_filtro': Disciplina.objects.all().order_by('nome'),
        'disciplinas': Disciplina.objects.all().order_by('nome'),
        'bancas': Banca.objects.all().order_by('nome'),
        'instituicoes': Instituicao.objects.all().order_by('nome'),
        'anos': Questao.objects.exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano'),
    })
    
    return render(request, 'gestao/listar_questoes.html', context)

# =======================================================================
# AS DEMAIS VIEWS (adicionar, editar, deletar, etc.) PERMANECEM AS MESMAS,
# POIS SÃO FUNCIONALIDADES EXCLUSIVAS DO PAINEL DE GESTÃO.
# =======================================================================

@user_passes_test(is_staff_member)
@login_required
def adicionar_questao(request):
    if request.method == 'POST':
        form = GestaoQuestaoForm(request.POST, request.FILES)
        if form.is_valid():
            questao = form.save(commit=False)
            questao.criada_por = request.user
            questao.save()
            messages.success(request, 'Questão adicionada com sucesso!')
            return redirect('gestao:listar_questoes')
    else:
        form = GestaoQuestaoForm()
        
    context = { 'form': form, 'titulo': 'Adicionar Nova Questão' }
    return render(request, 'gestao/form_questao.html', context)

@user_passes_test(is_staff_member)
@login_required
def editar_questao(request, questao_id):
    questao = get_object_or_404(Questao, id=questao_id)
    if request.method == 'POST':
        form = GestaoQuestaoForm(request.POST, request.FILES, instance=questao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Questão atualizada com sucesso!')
            return redirect('gestao:listar_questoes')
    else:
        form = GestaoQuestaoForm(instance=questao)

    context = { 'form': form, 'titulo': f'Editar Questão ({questao.codigo})' }
    return render(request, 'gestao/form_questao.html', context)

@user_passes_test(is_staff_member)
@login_required
def deletar_questao(request, questao_id):
    questao = get_object_or_404(Questao, id=questao_id)
    if request.method == 'POST':
        questao.delete()
        messages.success(request, 'Questão deletada com sucesso.')
        return redirect('gestao:listar_questoes')

    return render(request, 'gestao/confirmar_delete.html', {'questao': questao})

@user_passes_test(is_staff_member)
@login_required
@require_POST
def adicionar_entidade_simples(request):
    form = EntidadeSimplesForm(request.POST)
    if form.is_valid():
        nome = form.cleaned_data['nome']
        tipo_entidade = request.POST.get('tipo_entidade')
        
        ModelMap = { 'disciplina': Disciplina, 'banca': Banca, 'instituicao': Instituicao }
        Model = ModelMap.get(tipo_entidade)
        if not Model:
            return JsonResponse({'status': 'error', 'message': 'Tipo de entidade inválido.'}, status=400)
        if Model.objects.filter(nome__iexact=nome).exists():
            return JsonResponse({'status': 'error', 'message': f'Já existe um item com este nome.'}, status=400)

        try:
            entidade = Model.objects.create(nome=nome)
            return JsonResponse({ 'status': 'success', 'entidade': {'id': entidade.id, 'nome': entidade.nome} })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)

@user_passes_test(is_staff_member)
@login_required
@require_POST
def adicionar_assunto(request):
    form = AssuntoForm(request.POST)
    if form.is_valid():
        nome = form.cleaned_data['nome']
        disciplina = form.cleaned_data['disciplina']
        
        if Assunto.objects.filter(nome__iexact=nome, disciplina=disciplina).exists():
            return JsonResponse({'status': 'error', 'message': 'Já existe um assunto com este nome para esta disciplina.'}, status=400)

        try:
            assunto = Assunto.objects.create(nome=nome, disciplina=disciplina)
            return JsonResponse({ 'status': 'success', 'assunto': {'id': assunto.id, 'nome': assunto.nome, 'disciplina': disciplina.nome} })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)

@user_passes_test(is_staff_member)
@login_required
def dashboard_gestao(request):
    total_questoes = Questao.objects.count()
    # =======================================================================
    # ADIÇÃO: Contagem de notificações pendentes
    # =======================================================================
    notificacoes_pendentes = Notificacao.objects.filter(status=Notificacao.Status.PENDENTE).count()
    
    context = {
        'total_questoes': total_questoes,
        'notificacoes_pendentes': notificacoes_pendentes
    }
    return render(request, 'gestao/dashboard.html', context)


@require_POST
@user_passes_test(is_staff_member)
def notificacoes_acoes_em_massa(request):
    try:
        data = json.loads(request.body)
        notification_ids = data.get('ids', [])
        action = data.get('action')

        if not notification_ids or not action:
            return JsonResponse({'status': 'error', 'message': 'IDs ou ação ausentes.'}, status=400)

        # Usamos o modelo Notificacao importado de 'pratica'
        queryset = Notificacao.objects.filter(id__in=notification_ids)

        if action == 'resolver':
            queryset.update(status=Notificacao.Status.RESOLVIDO, resolvido_por=request.user, data_resolucao=timezone.now())
        elif action == 'arquivar':
            queryset.update(status=Notificacao.Status.ARQUIVADO, data_arquivamento=timezone.now())
        elif action == 'excluir':
            # Ação para a limpeza manual de itens arquivados
            queryset.filter(status=Notificacao.Status.ARQUIVADO).delete()
        else:
            return JsonResponse({'status': 'error', 'message': 'Ação inválida.'}, status=400)

        return JsonResponse({'status': 'success', 'message': 'Ação aplicada com sucesso!'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    

# =======================================================================
# INÍCIO: NOVAS VIEWS PARA GERENCIAR NOTIFICAÇÕES
# =======================================================================


@user_passes_test(is_staff_member)
@login_required
def listar_notificacoes(request):
    # ===================================================================
    # MODIFICAÇÃO 1: Captura do novo filtro 'q' para a pesquisa global
    # ===================================================================
    status_filtro = request.GET.get('status', 'PENDENTE')
    tipo_erro_filtro = request.GET.get('tipo_erro', '')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    questao_codigo_filtro = request.GET.get('questao_codigo', '')
    termo_busca = request.GET.get('q', '') # Novo filtro para o termo de busca

    # Queryset inicial com anotação (sem alterações)
    report_count_subquery = Notificacao.objects.filter(
        questao_id=OuterRef('questao_id')
    ).values('questao_id').annotate(count=Count('id')).values('count')

    notificacoes_list = Notificacao.objects.select_related(
        'questao', 'usuario_reportou__userprofile', 'resolvido_por'
    ).annotate(
        questao_report_count=Subquery(report_count_subquery)
    ).order_by('-data_criacao')
    
    # ===================================================================
    # MODIFICAÇÃO 2: Aplicação do filtro de pesquisa global com Q objects
    # ===================================================================
    if termo_busca:
        notificacoes_list = notificacoes_list.filter(
            Q(questao__codigo__icontains=termo_busca) |
            Q(descricao__icontains=termo_busca) |
            Q(usuario_reportou__userprofile__nome__icontains=termo_busca) |
            Q(usuario_reportou__email__icontains=termo_busca)
        )

    # Aplicação dos outros filtros (sem alterações)
    if status_filtro and status_filtro != 'TODAS':
        notificacoes_list = notificacoes_list.filter(status=status_filtro)
    if tipo_erro_filtro:
        notificacoes_list = notificacoes_list.filter(tipo_erro=tipo_erro_filtro)
    if questao_codigo_filtro:
        notificacoes_list = notificacoes_list.filter(questao__codigo__iexact=questao_codigo_filtro)
    
    try:
        if data_inicio:
            notificacoes_list = notificacoes_list.filter(data_criacao__date__gte=data_inicio)
        if data_fim:
            notificacoes_list = notificacoes_list.filter(data_criacao__date__lte=data_fim)
    except ValidationError:
        messages.error(request, 'Formato de data inválido. Por favor, utilize o formato AAAA-MM-DD.')
        
    # Cálculo das estatísticas e questões mais reportadas (sem alterações)
    uma_semana_atras = timezone.now() - timedelta(days=7)
    stats = {
        'pendentes_total': Notificacao.objects.filter(status=Notificacao.Status.PENDENTE).count(),
        'resolvidas_7_dias': Notificacao.objects.filter(status=Notificacao.Status.RESOLVIDO, data_resolucao__gte=uma_semana_atras).count(),
        'arquivadas_7_dias': Notificacao.objects.filter(status=Notificacao.Status.ARQUIVADO, data_arquivamento__gte=uma_semana_atras).count(),
        'total_notificacoes': Notificacao.objects.count()
    }
    stats['questoes_mais_reportadas'] = Notificacao.objects.values(
        'questao_id', 'questao__codigo'
    ).annotate(num_reports=Count('id')).order_by('-num_reports')[:5]

    # ===================================================================
    # MODIFICAÇÃO 3: Adiciona 'termo_busca' à lógica de reset da paginação
    # ===================================================================
    filters_applied = any([tipo_erro_filtro, data_inicio, data_fim, questao_codigo_filtro, termo_busca])
    paginator = Paginator(notificacoes_list, 10)
    page_number = 1 if filters_applied else request.GET.get('page', 1)
    
    try:
        notificacoes_paginadas = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        notificacoes_paginadas = paginator.page(paginator.num_pages if paginator.num_pages > 0 else 1)

    # Lógica de customização dos números de página (sem alterações)
    page_numbers = []
    # ... (o resto da sua lógica de paginação) ...
    current_page = notificacoes_paginadas.number; total_pages = paginator.num_pages
    if total_pages <= 7: page_numbers = list(range(1, total_pages + 1))
    else:
        if current_page <= 4: page_numbers = list(range(1, 6)) + ['...', total_pages]
        elif current_page >= total_pages - 3: page_numbers = [1, '...'] + list(range(total_pages - 4, total_pages + 1))
        else: page_numbers = [1, '...', current_page - 1, current_page, current_page + 1, '...', total_pages]

    # ===================================================================
    # MODIFICAÇÃO 4: Adiciona 'termo_busca_ativo' ao contexto final
    # ===================================================================
    context = {
        'notificacoes': notificacoes_paginadas,
        'page_numbers': page_numbers, 
        'status_ativo': status_filtro,
        'tipos_de_erro': Notificacao.TipoErro.choices,
        'tipo_erro_ativo': tipo_erro_filtro,
        'data_inicio_buscada': data_inicio,
        'data_fim_buscada': data_fim,
        'stats': stats,
        'questao_codigo_ativo': questao_codigo_filtro,
        'termo_busca_ativo': termo_busca,
    }
    return render(request, 'gestao/listar_notificacoes.html', context)


@user_passes_test(is_staff_member)
@login_required
@require_POST
def resolver_notificacao(request, notificacao_id):
    notificacao = get_object_or_404(Notificacao, id=notificacao_id)
    
    # ===================================================================
    # ADIÇÃO: Captura a URL de retorno a partir do Referer (de onde o usuário veio)
    # Isso preserva todos os filtros como ?status=PENDENTE&page=2
    # O fallback é a URL base, por segurança.
    # ===================================================================
    redirect_url = request.META.get('HTTP_REFERER', reverse('gestao:listar_notificacoes'))

    if notificacao.status == Notificacao.Status.PENDENTE:
        notificacao.status = Notificacao.Status.RESOLVIDO
        notificacao.resolvido_por = request.user
        notificacao.data_resolucao = timezone.now()
        notificacao.save()

        # A lógica de e-mail permanece a mesma
        if notificacao.usuario_reportou and notificacao.usuario_reportou.email:
            try:
                enviar_email_com_template(
                    request,
                    subject=f'Sua notificação sobre a questão {notificacao.questao.codigo} foi resolvida!',
                    template_name='gestao/email_notificacao_resolvida.html',
                    context={'user': notificacao.usuario_reportou, 'questao': notificacao.questao},
                    recipient_list=[notificacao.usuario_reportou.email]
                )
                messages.success(request, f'Notificação para a questão {notificacao.questao.codigo} marcada como resolvida e o usuário foi notificado.')
            except Exception as e:
                messages.warning(request, f'Notificação resolvida, mas falhou ao enviar e-mail: {e}')
        else:
            messages.success(request, f'Notificação para a questão {notificacao.questao.codigo} marcada como resolvida.')
    else:
        messages.warning(request, 'Esta notificação já havia sido resolvida.')

    # Redireciona para a URL capturada, em vez de uma URL fixa
    return redirect(redirect_url)


@user_passes_test(is_staff_member)
@login_required
@require_POST
def arquivar_notificacao(request, notificacao_id):
    notificacao = get_object_or_404(Notificacao, id=notificacao_id, status=Notificacao.Status.RESOLVIDO)
    
    # ===================================================================
    # ADIÇÃO: Captura a URL exata de retorno para manter a paginação correta
    # ===================================================================
    redirect_url = request.META.get('HTTP_REFERER', f"{reverse('gestao:listar_notificacoes')}?status=RESOLVIDO")
    
    notificacao.status = Notificacao.Status.ARQUIVADO
    notificacao.data_arquivamento = timezone.now()
    notificacao.save()
    
    messages.success(request, f'Notificação para a questão {notificacao.questao.codigo} foi arquivada.')
    
    # Redireciona de volta para a mesma página de onde o usuário veio
    return redirect(redirect_url)


@user_passes_test(is_staff_member)
@login_required
@require_POST
def desarquivar_notificacao(request, notificacao_id):
    notificacao = get_object_or_404(Notificacao, id=notificacao_id, status=Notificacao.Status.ARQUIVADO)
    
    # ===================================================================
    # ADIÇÃO: Captura a URL exata de retorno para manter a paginação correta
    # ===================================================================
    redirect_url = request.META.get('HTTP_REFERER', f"{reverse('gestao:listar_notificacoes')}?status=ARQUIVADO")
    
    notificacao.status = Notificacao.Status.RESOLVIDO
    notificacao.data_arquivamento = None
    notificacao.save()
    
    messages.info(request, f'Notificação para a questão {notificacao.questao.codigo} foi restaurada.')
    
    # Redireciona de volta para a mesma página de onde o usuário veio
    return redirect(redirect_url)

# ===================================================================
# NOVA VIEW PARA O MODAL DE VISUALIZAÇÃO RÁPIDA
# ===================================================================
@user_passes_test(is_staff_member)
@login_required
def visualizar_questao_ajax(request, questao_id):
    try:
        # Busca a questão ou retorna um erro 404 se não encontrar
        questao = get_object_or_404(Questao, id=questao_id)

        # Prepara os dados para serem enviados como JSON
        data = {
            'status': 'success',
            'codigo': questao.codigo,
            'enunciado': markdown.markdown(questao.enunciado), # Converte markdown para HTML
            'alternativas': questao.get_alternativas_dict(), # Usa o método do modelo para pegar as alternativas
            'gabarito': questao.gabarito
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)