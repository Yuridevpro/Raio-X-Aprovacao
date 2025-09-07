# gestao/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from pratica.models import Notificacao
from django.utils import timezone
from usuarios.views import enviar_email_com_template
from questoes.models import Questao, Disciplina, Banca, Instituicao, Assunto
from questoes.forms import GestaoQuestaoForm, EntidadeSimplesForm, AssuntoForm
from django.urls import reverse
from questoes.utils import paginar_itens, filtrar_e_paginar_questoes
from django.db.models import Q, Count, Max, Prefetch, Exists, OuterRef
import json
from django.core.exceptions import ValidationError
import markdown



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
    lista_questoes = Questao.objects.all().order_by('-id')


    # 2. Chama a função central para fazer todo o trabalho pesado de filtrar e paginar.
    context = filtrar_e_paginar_questoes(request, lista_questoes, items_per_page=20)

    

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




# =======================================================================
# INÍCIO: NOVAS VIEWS PARA GERENCIAR NOTIFICAÇÕES
# =======================================================================
from questoes.utils import paginar_itens




@user_passes_test(is_staff_member)
@login_required
def listar_notificacoes(request):
    """
    Exibe a página de gerenciamento de notificações, com os reports agrupados por questão.
    """
    status_filtro = request.GET.get('status', 'PENDENTE')
    
    # --- LÓGICA DA CONSULTA ---
    # 1. Começamos com questões que têm pelo menos uma notificação.
    #    Isso evita que questões com reports já deletados apareçam na aba "Todos".
    base_queryset = Questao.objects.annotate(
        num_notificacoes=Count('notificacoes')
    ).filter(num_notificacoes__gt=0)
    
    # 2. Nas abas específicas (Pendente, Corrigido, etc.), garantimos que a questão
    #    tenha pelo menos um report com aquele status.
    if status_filtro != 'TODAS':
        reports_na_aba_atual = Notificacao.objects.filter(questao_id=OuterRef('pk'), status=status_filtro)
        base_queryset = base_queryset.filter(Exists(reports_na_aba_atual))

    # 3. Anotamos os dados para cada card:
    #    - num_reports: A contagem de reports, respeitando o filtro da aba.
    #    - ultima_notificacao: A data do report mais recente, para ordenação.
    filtro_anotacao = Q(notificacoes__status=status_filtro) if status_filtro != 'TODAS' else Q()
    
    questoes_reportadas = base_queryset.annotate(
        num_reports=Count('notificacoes', filter=filtro_anotacao),
        ultima_notificacao=Max('notificacoes__data_criacao', filter=filtro_anotacao)
    ).order_by('-ultima_notificacao')

    # 4. Usamos Prefetch para carregar os detalhes dos reports de forma otimizada.
    prefetch_queryset = Notificacao.objects.select_related('usuario_reportou__userprofile')
    if status_filtro != 'TODAS':
        prefetch_queryset = prefetch_queryset.filter(status=status_filtro)
        
    questoes_reportadas = questoes_reportadas.prefetch_related(
        Prefetch('notificacoes', queryset=prefetch_queryset.order_by('-data_criacao'), to_attr='reports_filtrados')
    )

    # 5. Paginação
    page_obj, page_numbers = paginar_itens(request, questoes_reportadas, 10)

    # 6. Estatísticas para os cards do topo
    stats = {
        'pendentes_total': Notificacao.objects.filter(status=Notificacao.Status.PENDENTE).count(),
        'resolvidas_total': Notificacao.objects.filter(status=Notificacao.Status.RESOLVIDO).count(),
        'rejeitadas_total': Notificacao.objects.filter(status=Notificacao.Status.REJEITADO).count(),
    }

    context = {
        'questoes_agrupadas': page_obj,
        'page_numbers': page_numbers,
        'status_ativo': status_filtro,
        'stats': stats,
    }
    
    return render(request, 'gestao/listar_notificacoes_agrupadas.html', context)


@require_POST
@user_passes_test(is_staff_member)
@login_required
def notificacao_acao_agrupada(request, questao_id):
    """ Aplica uma ação em massa a todos os reports de um status para uma questão. """
    questao = get_object_or_404(Questao, id=questao_id)
    action = request.POST.get('action')
    status_original = request.POST.get('status_original', 'PENDENTE')
    notificacoes = Notificacao.objects.filter(questao=questao, status=status_original)
    
    if action == 'resolver':
        # --- INÍCIO DA LÓGICA DE E-MAIL ---
        # 1. Pega a lista de e-mails *antes* de atualizar o status
        emails_para_notificar = list(
            notificacoes.exclude(usuario_reportou__email__isnull=True)
                        .exclude(usuario_reportou__email__exact='')
                        .values_list('usuario_reportou__email', flat=True)
                        .distinct()
        )
        # --- FIM DA LÓGICA DE E-MAIL ---

        count = notificacoes.update(status=Notificacao.Status.RESOLVIDO, resolvido_por=request.user, data_resolucao=timezone.now())
        
        # --- INÍCIO DA LÓGICA DE E-MAIL ---
        # 2. Envia os e-mails
        if emails_para_notificar:
            try:
                enviar_email_com_template(
                    request,
                    subject=f'Sua notificação sobre a questão {questao.codigo} foi resolvida!',
                    template_name='gestao/email_notificacao_resolvida.html',
                    # O contexto é genérico, pois o e-mail é o mesmo para todos
                    context={'user': None, 'questao': questao},
                    # Envia para múltiplos destinatários de uma vez
                    recipient_list=emails_para_notificar
                )
                messages.success(request, f'{count} report(s) marcados como "Corrigido". E-mails de notificação enviados para {len(emails_para_notificar)} usuário(s).')
            except Exception as e:
                messages.warning(request, f'{count} report(s) marcados como "Corrigido", mas falhou ao enviar e-mails de notificação: {e}')
        else:
            messages.success(request, f'{count} report(s) da questão {questao.codigo} marcados como "Corrigido".')
        # --- FIM DA LÓGICA DE E-MAIL ---
            
    elif action == 'rejeitar':
        count = notificacoes.update(status=Notificacao.Status.REJEITADO)
        messages.warning(request, f'{count} report(s) da questão {questao.codigo} foram rejeitados.')
    elif action == 'excluir':
        if status_original in ['RESOLVIDO', 'REJEITADO']:
            count, _ = notificacoes.delete()
            messages.error(request, f'{count} report(s) da questão {questao.codigo} foram excluídos permanentemente.')
        else:
            messages.error(request, 'A exclusão só é permitida para reports Corrigidos ou Rejeitados.')
    else:
        messages.error(request, 'Ação inválida.')
    return redirect(request.META.get('HTTP_REFERER', reverse('gestao:listar_notificacoes')))


@require_POST
@user_passes_test(is_staff_member)
def notificacoes_acoes_em_massa(request):
    """ View para as ações da barra superior (com checkboxes) """
    try:
        data = json.loads(request.body)
        questao_ids = data.get('ids', [])
        action = data.get('action')
        status_original = data.get('status_original', 'PENDENTE')

        if not questao_ids or not action:
            return JsonResponse({'status': 'error', 'message': 'IDs ou ação ausentes.'}, status=400)

        queryset = Notificacao.objects.filter(questao_id__in=questao_ids, status=status_original)

        if action == 'resolver':
            # Lógica de e-mail para ações em massa
            emails_para_notificar = list(queryset.exclude(usuario_reportou__email__isnull=True).exclude(usuario_reportou__email__exact='').values_list('usuario_reportou__email', flat=True).distinct())
            
            queryset.update(status=Notificacao.Status.RESOLVIDO, resolvido_por=request.user, data_resolucao=timezone.now())
            
            if emails_para_notificar:
                # O ideal aqui seria usar uma task assíncrona (Celery), mas para um volume baixo, isso funciona.
                for questao_id in questao_ids:
                    questao = Questao.objects.get(id=questao_id)
                    enviar_email_com_template(
                        request, subject=f'Sua notificação sobre a questão {questao.codigo} foi resolvida!',
                        template_name='gestao/email_notificacao_resolvida.html',
                        context={'user': None, 'questao': questao},
                        recipient_list=emails_para_notificar # Envia para todos de uma vez (idealmente seria por questão)
                    )
        
        elif action == 'rejeitar':
            queryset.update(status=Notificacao.Status.REJEITADO)
        
        elif action == 'excluir':
            if status_original in ['RESOLVIDO', 'REJEITADO']:
                queryset.delete()
            else:
                return JsonResponse({'status': 'error', 'message': 'A exclusão só é permitida para itens Corrigidos ou Rejeitados.'}, status=400)
        else:
            return JsonResponse({'status': 'error', 'message': 'Ação inválida.'}, status=400)

        return JsonResponse({'status': 'success', 'message': 'Ação aplicada com sucesso!'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    
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
    

