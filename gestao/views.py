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
from django.contrib.auth.models import User
from .forms import StaffUserForm 
 # Certifique-se que JsonResponse está importado
from .models import SolicitacaoExclusao
from .forms import ExclusaoUsuarioForm # Importe o novo formulário


# =======================================================================
# IMPORTAÇÃO DA NOSSA NOVA FUNÇÃO CENTRALIZADA
# =======================================================================
from questoes.utils import filtrar_e_paginar_questoes


def is_staff_member(user):
    return user.is_staff

# gestao/views.py

# Adicione o novo modelo aos seus imports
from .models import SolicitacaoExclusao
# ... outros imports

# gestao/views.py

@user_passes_test(is_staff_member)
@login_required
def dashboard_gestao(request):
    total_questoes = Questao.objects.count()
    notificacoes_pendentes = Notificacao.objects.filter(status=Notificacao.Status.PENDENTE).count()
    
    # ESTA PARTE FAZ A CONTAGEM CORRETA
    solicitacoes_pendentes_count = 0
    if request.user.is_superuser:
        solicitacoes_pendentes_count = SolicitacaoExclusao.objects.filter(
            status=SolicitacaoExclusao.Status.PENDENTE
        ).count()
    
    context = {
        'total_questoes': total_questoes,
        'notificacoes_pendentes': notificacoes_pendentes,
        'solicitacoes_pendentes_count': solicitacoes_pendentes_count, # A variável é enviada para o template
    }
    return render(request, 'gestao/dashboard.html', context)
    
    context = {
        'total_questoes': total_questoes,
        'notificacoes_pendentes': notificacoes_pendentes,
        'solicitacoes_pendentes_count': solicitacoes_pendentes_count, # Adicionado ao contexto
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

@login_required
@user_passes_test(is_staff_member)
@require_POST # A exclusão deve ser sempre via POST
def deletar_questao(request, questao_id):
    """
    Deleta uma questão e retorna uma resposta JSON para a requisição AJAX.
    """
    questao = get_object_or_404(Questao, id=questao_id)
    
    try:
        questao_codigo = questao.codigo
        questao.delete()
        return JsonResponse({
            'status': 'success',
            'message': f'A questão "{questao_codigo}" foi excluída com sucesso.',
            'deleted_questao_id': questao_id
        })
    except Exception as e:
        # Captura erros, como erros de PROTECT do banco de dados
        return JsonResponse({
            'status': 'error',
            'message': f'Não foi possível excluir a questão. Erro: {str(e)}'
        }, status=500)

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


# gestao/views.py
# ... (outros imports)

@require_POST
@user_passes_test(is_staff_member)
@login_required
def notificacao_acao_agrupada(request, questao_id):
    """
    Aplica uma ação em massa a todos os reports de um status para uma questão.
    AGORA RETORNA JSON para funcionar com AJAX.
    """
    questao = get_object_or_404(Questao, id=questao_id)
    action = request.POST.get('action')
    status_original = request.POST.get('status_original', 'PENDENTE')
    notificacoes = Notificacao.objects.filter(questao=questao, status=status_original)
    
    count = notificacoes.count()
    message = ""

    if action == 'resolver':
        emails_para_notificar = list(
            notificacoes.exclude(usuario_reportou__email__isnull=True)
                        .exclude(usuario_reportou__email__exact='')
                        .values_list('usuario_reportou__email', flat=True).distinct()
        )
        notificacoes.update(status=Notificacao.Status.RESOLVIDO, resolvido_por=request.user, data_resolucao=timezone.now())
        
        # Lógica de e-mail (não bloqueante)
        if emails_para_notificar:
            try:
                enviar_email_com_template(
                    request,
                    subject=f'Sua notificação sobre a questão {questao.codigo} foi resolvida!',
                    template_name='gestao/email_notificacao_resolvida.html',
                    context={'user': None, 'questao': questao},
                    recipient_list=emails_para_notificar
                )
                message = f'{count} report(s) da questão {questao.codigo} marcados como "Corrigido". E-mails de notificação enviados.'
            except Exception:
                message = f'{count} report(s) marcados como "Corrigido", mas falhou ao enviar e-mails de notificação.'
        else:
            message = f'{count} report(s) da questão {questao.codigo} marcados como "Corrigido".'
        
        return JsonResponse({'status': 'success', 'message': message, 'removed_card_id': f'card-group-{questao.id}'})

    elif action == 'rejeitar':
        notificacoes.update(status=Notificacao.Status.REJEITADO)
        message = f'{count} report(s) da questão {questao.codigo} foram rejeitados.'
        return JsonResponse({'status': 'success', 'message': message, 'removed_card_id': f'card-group-{questao.id}'})

    elif action == 'excluir':
        if status_original in ['RESOLVIDO', 'REJEITADO']:
            count, _ = notificacoes.delete()
            message = f'{count} report(s) da questão {questao.codigo} foram excluídos permanentemente.'
            return JsonResponse({'status': 'success', 'message': message, 'removed_card_id': f'card-group-{questao.id}'})
        else:
            return JsonResponse({'status': 'error', 'message': 'A exclusão só é permitida para reports Corrigidos ou Rejeitados.'}, status=403)
    
    return JsonResponse({'status': 'error', 'message': 'Ação inválida.'}, status=400)


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
    

# gestao/views.py



# =======================================================================
# INÍCIO: NOVAS VIEWS PARA GERENCIAR USUÁRIOS (APENAS SUPERUSER)
# =======================================================================

# gestao/views.py

@login_required
@user_passes_test(is_staff_member)
def listar_usuarios(request):
    base_queryset = User.objects.exclude(id=request.user.id)
    if not request.user.is_superuser:
        base_queryset = base_queryset.exclude(is_superuser=True)
    base_queryset = base_queryset.order_by('username')
    filtro_q = request.GET.get('q', '').strip()
    filtro_permissao = request.GET.get('permissao', '')
    if filtro_q:
        base_queryset = base_queryset.filter(
            Q(username__icontains=filtro_q) | Q(email__icontains=filtro_q)
        )
    if filtro_permissao == 'superuser':
        if request.user.is_superuser:
            base_queryset = base_queryset.filter(is_superuser=True)
    elif filtro_permissao == 'staff':
        base_queryset = base_queryset.filter(is_staff=True, is_superuser=False)
    elif filtro_permissao == 'comum':
        base_queryset = base_queryset.filter(is_staff=False)
    
    usuarios_paginados, page_numbers = paginar_itens(request, base_queryset, items_per_page=9) # Ajuste a paginação se desejar

    # Monta o contexto para o template
    context = {
        'usuarios': usuarios_paginados,
        'paginated_object': usuarios_paginados,
        'page_numbers': page_numbers,
        'filtro_q': filtro_q,
        'filtro_permissao': filtro_permissao,
        # =======================================================================
        # ADIÇÃO: Passa a contagem total de itens (pós-filtro) para o template
        # =======================================================================
        'total_usuarios': usuarios_paginados.paginator.count,
    }
    return render(request, 'gestao/listar_usuarios.html', context)
# =======================================================================
# FIM DO BLOCO MODIFICADO
# =======================================================================



@login_required
@user_passes_test(lambda u: u.is_superuser)
def editar_usuario_staff(request, user_id):
    usuario_alvo = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = StaffUserForm(request.POST, instance=usuario_alvo)
        if form.is_valid():
            # =======================================================================
            # INÍCIO DA MUDANÇA: Verificação de segurança adicional
            # =======================================================================
            is_staff_novo = form.cleaned_data.get('is_staff')
            if usuario_alvo.is_superuser and not is_staff_novo:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Ação negada: Um Superusuário não pode ser removido do status "Membro da Equipe".'
                }, status=403) # 403 Forbidden
            # =======================================================================
            # FIM DA MUDANÇA
            # =======================================================================
            
            form.save()
            return JsonResponse({
                'status': 'success',
                'message': f'Permissões do usuário {usuario_alvo.username} atualizadas com sucesso.'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Ocorreu um erro de validação.',
                'errors': form.errors
            }, status=400)

    else:
        form = StaffUserForm(instance=usuario_alvo)

    context = {
        'form': form, 'usuario_alvo': usuario_alvo, 'titulo': f'Editar Permissões de {usuario_alvo.username}'
    }
    return render(request, 'gestao/form_usuario_staff.html', context)





# =======================================================================
# INÍCIO DO BLOCO NOVO: View para Ações em Massa de Questões
# =======================================================================
@login_required
@user_passes_test(is_staff_member)
@require_POST
def questoes_acoes_em_massa(request):
    """
    Processa ações em massa (como deletar) para as questões selecionadas.
    """
    try:
        data = json.loads(request.body)
        questao_ids = data.get('ids', [])
        action = data.get('action')

        if not questao_ids or not action:
            return JsonResponse({'status': 'error', 'message': 'IDs ou ação ausentes.'}, status=400)

        queryset = Questao.objects.filter(id__in=questao_ids)

        if action == 'delete':
            count, _ = queryset.delete()
            return JsonResponse({
                'status': 'success',
                'message': f'{count} questão(ões) foram excluídas com sucesso.'
            })
        else:
            return JsonResponse({'status': 'error', 'message': 'Ação inválida.'}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
# =======================================================================
# FIM DO BLOCO NOVO

# =======================================================================
# INÍCIO DO BLOCO NOVO: View para promover um usuário a Superusuário
# =======================================================================
@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def promover_a_superuser(request, user_id):
    """
    Promove um usuário existente a superusuário.
    Ação de alto risco, acessível apenas por outros superusuários.
    """
    usuario_alvo = get_object_or_404(User, id=user_id)

    # Verificação de segurança: um superusuário não pode promover a si mesmo.
    if usuario_alvo == request.user:
        return JsonResponse({
            'status': 'error',
            'message': 'Você não pode alterar suas próprias permissões de superusuário.'
        }, status=403)

    try:
        # A promoção para superusuário também exige que o usuário seja staff.
        usuario_alvo.is_superuser = True
        usuario_alvo.is_staff = True # Superusuários devem ser staff por definição.
        usuario_alvo.save(update_fields=['is_superuser', 'is_staff'])
        
        return JsonResponse({
            'status': 'success',
            'message': f'O usuário "{usuario_alvo.username}" foi promovido a Superusuário com sucesso.'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ocorreu um erro inesperado ao promover o usuário: {str(e)}'
        }, status=500)
# =======================================================================
# FIM DO BLOCO NOVO
# =======================================================================

# =======================================================================
# INÍCIO DO BLOCO NOVO: View para despromover um Superusuário
# =======================================================================
@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def despromover_de_superuser(request, user_id):
    """
    Remove as permissões de superusuário de um usuário.
    Ação de alto risco com salvaguardas.
    """
    usuario_alvo = get_object_or_404(User, id=user_id)

    # Verificação de segurança 1: Não pode despromover a si mesmo.
    if usuario_alvo == request.user:
        return JsonResponse({'status': 'error', 'message': 'Você não pode remover suas próprias permissões de superusuário.'}, status=403)

    # Verificação de segurança 2: Não pode despromover o último superusuário ativo.
    if User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Não é possível remover as permissões do único superusuário do sistema.'}, status=403)

    try:
        usuario_alvo.is_superuser = False
        usuario_alvo.save(update_fields=['is_superuser'])
        return JsonResponse({
            'status': 'success',
            'message': f'O usuário "{usuario_alvo.username}" não é mais um Superusuário. Ele ainda é um Membro da Equipe.'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro inesperado: {str(e)}'}, status=500)
# =======================================================================
# FIM DO BLOCO NOVO
# =======================================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def deletar_usuario(request, user_id):
    usuario_alvo = get_object_or_404(User, id=user_id)
    form = ExclusaoUsuarioForm(request.POST) # Usa o novo formulário unificado

    # Verificações de segurança (inalteradas)
    if usuario_alvo == request.user:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Você não pode excluir sua própria conta.'}, status=403)
    if usuario_alvo.is_superuser and User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Não é possível excluir o único superusuário do sistema.'}, status=403)

    if form.is_valid():
        motivo_predefinido_chave = form.cleaned_data['motivo_predefinido']
        motivo_predefinido_texto = dict(form.fields['motivo_predefinido'].choices)[motivo_predefinido_chave]
        justificativa = form.cleaned_data.get('justificativa', '') # Campo opcional para superuser
        
        # Constrói o motivo completo para o e-mail
        motivo_final_para_email = f"{motivo_predefinido_texto}"
        if justificativa:
            motivo_final_para_email += f" (Detalhes: {justificativa})"
            
        email_alvo = usuario_alvo.email
        username_alvo = usuario_alvo.username

        if email_alvo:
            try:
                enviar_email_com_template(
                    request,
                    subject='Sua conta na plataforma Raio-X da Aprovação foi removida',
                    template_name='gestao/email_conta_excluida.html',
                    context={'user': usuario_alvo, 'motivo_texto': motivo_final_para_email},
                    recipient_list=[email_alvo]
                )
                usuario_alvo.delete()
                message = f'O usuário "{username_alvo}" foi excluído e notificado por e-mail com sucesso.'
            except Exception as e:
                usuario_alvo.delete()
                message = f'O usuário "{username_alvo}" foi excluído, mas ocorreu um erro ao enviar o e-mail: {e}'
        else:
            usuario_alvo.delete()
            message = f'O usuário "{username_alvo}" foi excluído. (Nenhuma notificação foi enviada por falta de e-mail).'

        return JsonResponse({'status': 'success', 'message': message, 'deleted_user_id': user_id })
    else:
        return JsonResponse({'status': 'error', 'message': 'Por favor, corrija os erros abaixo.', 'field_errors': form.errors}, status=400)


# =======================================================================
# View 'sugerir_exclusao_usuario' refatorada com o novo formulário
# =======================================================================
@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def sugerir_exclusao_usuario(request, user_id):
    usuario_alvo = get_object_or_404(User, id=user_id)
    form = ExclusaoUsuarioForm(request.POST) # Usa o formulário unificado

    # Verificações de segurança (inalteradas)
    if usuario_alvo.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Membros da equipe não podem sugerir a exclusão de superusuários.'}, status=403)
    if SolicitacaoExclusao.objects.filter(usuario_a_ser_excluido=usuario_alvo, status=SolicitacaoExclusao.Status.PENDENTE).exists():
        return JsonResponse({'status': 'error', 'message': 'Já existe uma solicitação de exclusão pendente para este usuário.'}, status=400)

    # Adiciona a validação de obrigatoriedade para o campo de justificativa
    form.fields['justificativa'].required = True
        
    if form.is_valid():
        motivo_predefinido_chave = form.cleaned_data['motivo_predefinido']
        motivo_predefinido_texto = dict(form.fields['motivo_predefinido'].choices)[motivo_predefinido_chave]
        justificativa = form.cleaned_data['justificativa']
        
        # Combina os dois campos para salvar no modelo de solicitação
        motivo_completo = f"Motivo: {motivo_predefinido_texto}\n\nJustificativa: {justificativa}"

        # =======================================================================
        # CORREÇÃO PRINCIPAL: Criar o objeto diretamente em vez de usar form.save()
        # =======================================================================
        SolicitacaoExclusao.objects.create(
            usuario_a_ser_excluido=usuario_alvo,
            solicitado_por=request.user,
            motivo=motivo_completo
        )
        
        return JsonResponse({'status': 'success', 'message': 'Sua sugestão de exclusão foi enviada para revisão por um superusuário.'})
    
    # Se o formulário for inválido
    return JsonResponse({'status': 'error', 'message': 'Por favor, corrija os erros abaixo.', 'field_errors': form.errors}, status=400)

# 2. View para Superusuários listarem as solicitações
@login_required
@user_passes_test(lambda u: u.is_superuser)
def listar_solicitacoes_exclusao(request):
    solicitacoes_list = SolicitacaoExclusao.objects.filter(
        status=SolicitacaoExclusao.Status.PENDENTE
    ).select_related('usuario_a_ser_excluido', 'solicitado_por').order_by('-data_solicitacao') # Boa prática adicionar um order_by

    solicitacoes_paginadas, page_numbers = paginar_itens(request, solicitacoes_list, items_per_page=10) # Aumentei para 5, 1 por página é muito pouco. Ajuste como preferir.

    context = {
        'solicitacoes': solicitacoes_paginadas,
        'paginated_object': solicitacoes_paginadas,
        'page_numbers': page_numbers,
        # =======================================================================
        # ADIÇÃO: Passa a contagem total de itens para o template
        # =======================================================================
        'total_solicitacoes': solicitacoes_paginadas.paginator.count,
    }
    return render(request, 'gestao/listar_solicitacoes_exclusao.html', context)


# 3. Views para Aprovar/Rejeitar (Ações do Superusuário)
# gestao/views.py

# ... (outros imports)

# =======================================================================
# INÍCIO DO BLOCO MODIFICADO: Views de Aprovar/Rejeitar com JSON
# =======================================================================
# =======================================================================
# INÍCIO DO BLOCO CORRIGIDO: View 'aprovar_solicitacao_exclusao'
# =======================================================================
@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def aprovar_solicitacao_exclusao(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoExclusao, id=solicitacao_id, status=SolicitacaoExclusao.Status.PENDENTE)
    usuario_a_deletar = solicitacao.usuario_a_ser_excluido

    # Verificações de segurança (inalteradas)
    if User.objects.filter(is_superuser=True, is_active=True).count() <= 1 and usuario_a_deletar.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Não é possível aprovar a exclusão do único superusuário.'}, status=403)

    try:
        username = usuario_a_deletar.username
        
        # =======================================================================
        # CORREÇÃO PRINCIPAL: Inverter a ordem das operações
        # =======================================================================
        
        # 1. PRIMEIRO, atualize e salve o status da solicitação
        solicitacao.status = SolicitacaoExclusao.Status.APROVADO
        solicitacao.revisado_por = request.user
        solicitacao.data_revisao = timezone.now()
        solicitacao.save()
        
        # 2. SÓ DEPOIS, delete o usuário
        usuario_a_deletar.delete()
        
        # =======================================================================
        
        return JsonResponse({
            'status': 'success',
            'message': f'A solicitação foi aprovada e o usuário {username} foi excluído.',
            'solicitacao_id': solicitacao_id
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro inesperado: {str(e)}'}, status=500)
# =======================================================================
# FIM DO BLOCO CORRIGIDO
# =======================================================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def rejeitar_solicitacao_exclusao(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoExclusao, id=solicitacao_id, status=SolicitacaoExclusao.Status.PENDENTE)
    
    try:
        solicitacao.status = SolicitacaoExclusao.Status.REJEITADO
        solicitacao.revisado_por = request.user
        solicitacao.data_revisao = timezone.now()
        solicitacao.save(update_fields=['status', 'revisado_por', 'data_revisao'])

        return JsonResponse({
            'status': 'success',
            'message': f'A solicitação para excluir o usuário "{solicitacao.usuario_a_ser_excluido.username}" foi rejeitada.',
            'solicitacao_id': solicitacao_id
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro: {str(e)}'}, status=500)
# =======================================================================
# FIM DO BLOCO MODIFICADO
# =======================================================================