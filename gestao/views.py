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
from .models import SolicitacaoExclusao, PromocaoSuperuser
from .forms import ExclusaoUsuarioForm
from .models import LogAtividade
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from datetime import datetime, timedelta
from questoes.utils import filtrar_e_paginar_questoes
import boto3
import os


def is_staff_member(user):
    return user.is_staff

@user_passes_test(is_staff_member)
@login_required
def dashboard_gestao(request):
    total_questoes = Questao.objects.count()
    notificacoes_pendentes = Notificacao.objects.filter(status=Notificacao.Status.PENDENTE).count()
    
    solicitacoes_pendentes_count = SolicitacaoExclusao.objects.filter(
        status=SolicitacaoExclusao.Status.PENDENTE
    ).count()
    
    context = {
        'total_questoes': total_questoes,
        'notificacoes_pendentes': notificacoes_pendentes,
        'solicitacoes_pendentes_count': solicitacoes_pendentes_count,
    }
    return render(request, 'gestao/dashboard.html', context)

@user_passes_test(is_staff_member)
@login_required
def listar_questoes_gestao(request):
    """
    View para listar questões no painel de gestão.
    Agora utiliza a função centralizada para filtros e paginação.
    """
    lista_questoes = Questao.objects.all().order_by('-id')
    context = filtrar_e_paginar_questoes(request, lista_questoes, items_per_page=20)

    # Adiciona ao contexto os formulários para os modais
    context.update({
        'disciplinas_para_filtro': Disciplina.objects.all().order_by('nome'),
        'disciplinas': Disciplina.objects.all().order_by('nome'),
        'bancas': Banca.objects.all().order_by('nome'),
        'instituicoes': Instituicao.objects.all().order_by('nome'),
        'anos': Questao.objects.exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano'),
        'entidade_simples_form': EntidadeSimplesForm(), # Formulário para Disciplina, Banca, Instituição
        'assunto_form': AssuntoForm(),                # Formulário para Assunto
    })
    
    return render(request, 'gestao/listar_questoes.html', context)

@user_passes_test(is_staff_member)
@login_required
def adicionar_questao(request):
    if request.method == 'POST':
        form = GestaoQuestaoForm(request.POST, request.FILES)
        if form.is_valid():
            questao = form.save(commit=False)
            questao.criada_por = request.user
            questao.save()  # Salva para obter o ID

            criar_log(
                ator=request.user,
                acao=LogAtividade.Acao.QUESTAO_CRIADA,
                alvo=questao,
                detalhes={'codigo_questao': questao.codigo}
            )

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

            criar_log(
                ator=request.user,
                acao=LogAtividade.Acao.QUESTAO_EDITADA,
                alvo=questao,
                detalhes={'codigo_questao': questao.codigo}
            )
            
            messages.success(request, 'Questão atualizada com sucesso!')
            return redirect('gestao:listar_questoes')
    else:
        form = GestaoQuestaoForm(instance=questao)

    context = { 'form': form, 'titulo': f'Editar Questão ({questao.codigo})' }
    return render(request, 'gestao/form_questao.html', context)

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

            criar_log(
                ator=request.user,
                acao=LogAtividade.Acao.ENTIDADE_CRIADA,
                alvo=entidade,
                detalhes={'tipo': tipo_entidade.capitalize(), 'nome': entidade.nome}
            )

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

            criar_log(
                ator=request.user,
                acao=LogAtividade.Acao.ASSUNTO_CRIADO,
                alvo=assunto,
                detalhes={'assunto': assunto.nome, 'disciplina': disciplina.nome}
            )
            
            return JsonResponse({ 'status': 'success', 'assunto': {'id': assunto.id, 'nome': assunto.nome, 'disciplina': disciplina.nome} })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'errors': form.errors.as_json()}, status=400)

@user_passes_test(is_staff_member)
@login_required
def listar_notificacoes(request):
    status_filtro = request.GET.get('status', 'PENDENTE')
    
    base_queryset = Questao.objects.annotate(
        num_notificacoes=Count('notificacoes')
    ).filter(num_notificacoes__gt=0)
    
    if status_filtro != 'TODAS':
        reports_na_aba_atual = Notificacao.objects.filter(questao_id=OuterRef('pk'), status=status_filtro)
        base_queryset = base_queryset.filter(Exists(reports_na_aba_atual))

    filtro_anotacao = Q(notificacoes__status=status_filtro) if status_filtro != 'TODAS' else Q()
    
    questoes_reportadas = base_queryset.annotate(
        num_reports=Count('notificacoes', filter=filtro_anotacao),
        ultima_notificacao=Max('notificacoes__data_criacao', filter=filtro_anotacao)
    ).order_by('-ultima_notificacao')

    prefetch_queryset = Notificacao.objects.select_related('usuario_reportou__userprofile')
    if status_filtro != 'TODAS':
        prefetch_queryset = prefetch_queryset.filter(status=status_filtro)
        
    questoes_reportadas = questoes_reportadas.prefetch_related(
        Prefetch('notificacoes', queryset=prefetch_queryset.order_by('-data_criacao'), to_attr='reports_filtrados')
    )

    page_obj, page_numbers = paginar_itens(request, questoes_reportadas, 10)

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
        
        criar_log(
            ator=request.user, acao=LogAtividade.Acao.NOTIFICACOES_RESOLVIDAS, alvo=questao,
            detalhes={'count': count, 'codigo_questao': questao.codigo}
        )

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
        
        criar_log(
            ator=request.user, acao=LogAtividade.Acao.NOTIFICACOES_REJEITADAS, alvo=questao,
            detalhes={'count': count, 'codigo_questao': questao.codigo}
        )
        
        message = f'{count} report(s) da questão {questao.codigo} foram rejeitados.'
        return JsonResponse({'status': 'success', 'message': message, 'removed_card_id': f'card-group-{questao.id}'})

    elif action == 'excluir':
        if status_original in ['RESOLVIDO', 'REJEITADO']:
            count, _ = notificacoes.delete()
            
            criar_log(
                ator=request.user, acao=LogAtividade.Acao.NOTIFICACOES_DELETADAS, alvo=questao,
                detalhes={'count': count, 'codigo_questao': questao.codigo, 'status_original': status_original}
            )

            message = f'{count} report(s) da questão {questao.codigo} foram excluídos permanentemente.'
            return JsonResponse({'status': 'success', 'message': message, 'removed_card_id': f'card-group-{questao.id}'})
        else:
            return JsonResponse({'status': 'error', 'message': 'A exclusão só é permitida para reports Corrigidos ou Rejeitados.'}, status=403)
    
    return JsonResponse({'status': 'error', 'message': 'Ação inválida.'}, status=400)


@require_POST
@user_passes_test(is_staff_member)
def notificacoes_acoes_em_massa(request):
    try:
        data = json.loads(request.body)
        questao_ids = data.get('ids', [])
        action = data.get('action')
        status_original = data.get('status_original', 'PENDENTE')

        if not questao_ids or not action:
            return JsonResponse({'status': 'error', 'message': 'IDs ou ação ausentes.'}, status=400)

        queryset = Notificacao.objects.filter(questao_id__in=questao_ids, status=status_original)

        # ANTES de executar a ação, iteramos para criar os logs
        for q_id in questao_ids:
            questao = get_object_or_404(Questao, id=q_id)
            count = queryset.filter(questao_id=q_id).count()

            if count > 0:
                if action == 'resolver':
                    log_acao = LogAtividade.Acao.NOTIFICACOES_RESOLVIDAS
                elif action == 'rejeitar':
                    log_acao = LogAtividade.Acao.NOTIFICACOES_REJEITADAS
                elif action == 'excluir' and status_original in ['RESOLVIDO', 'REJEITADO']:
                    log_acao = LogAtividade.Acao.NOTIFICACOES_DELETADAS
                else:
                    continue  # Pula para a próxima questão se a ação for inválida
                
                criar_log(
                    ator=request.user, acao=log_acao, alvo=questao,
                    detalhes={
                        'count': count, 'codigo_questao': questao.codigo, 
                        'status_original': status_original, 'motivo': 'Ação em massa'
                    }
                )

        # AGORA, executamos a ação no banco de dados
        if action == 'resolver':
            emails_para_notificar = list(queryset.exclude(usuario_reportou__email__isnull=True).exclude(usuario_reportou__email__exact='').values_list('usuario_reportou__email', flat=True).distinct())
            queryset.update(status=Notificacao.Status.RESOLVIDO, resolvido_por=request.user, data_resolucao=timezone.now())
            if emails_para_notificar:
                for questao_id in questao_ids:
                    questao = Questao.objects.get(id=questao_id)
                    enviar_email_com_template(
                        request, subject=f'Sua notificação sobre a questão {questao.codigo} foi resolvida!',
                        template_name='gestao/email_notificacao_resolvida.html',
                        context={'user': None, 'questao': questao},
                        recipient_list=emails_para_notificar
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

        return JsonResponse({'status': 'success', 'message': 'Ação aplicada com sucesso e registrada no log.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    
@user_passes_test(is_staff_member)
@login_required
@require_POST
def resolver_notificacao(request, notificacao_id):
    notificacao = get_object_or_404(Notificacao, id=notificacao_id)
    
    redirect_url = request.META.get('HTTP_REFERER', reverse('gestao:listar_notificacoes'))

    if notificacao.status == Notificacao.Status.PENDENTE:
        notificacao.status = Notificacao.Status.RESOLVIDO
        notificacao.resolvido_por = request.user
        notificacao.data_resolucao = timezone.now()
        notificacao.save()

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

    return redirect(redirect_url)

@user_passes_test(is_staff_member)
@login_required
def visualizar_questao_ajax(request, questao_id):
    try:
        questao = get_object_or_404(Questao, id=questao_id)
        data = {
            'status': 'success',
            'codigo': questao.codigo,
            'enunciado': markdown.markdown(questao.enunciado),
            'alternativas': questao.get_alternativas_dict(),
            'gabarito': questao.gabarito
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@user_passes_test(is_staff_member)
def listar_usuarios(request):
    base_queryset = User.objects.exclude(id=request.user.id)
    if not request.user.is_superuser:
        base_queryset = base_queryset.exclude(is_superuser=True)

    solicitacoes_pendentes = SolicitacaoExclusao.objects.filter(
        usuario_a_ser_excluido=OuterRef('pk'),
        status=SolicitacaoExclusao.Status.PENDENTE
    )
    base_queryset = base_queryset.annotate(
        tem_solicitacao_pendente=Exists(solicitacoes_pendentes)
    )

    base_queryset = base_queryset.order_by('-tem_solicitacao_pendente', 'username')

    filtro_q = request.GET.get('q', '').strip()
    filtro_permissao = request.GET.get('permissao', '')
    filtro_solicitacao = request.GET.get('solicitacao', '')

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

    if filtro_solicitacao == 'pendente':
        base_queryset = base_queryset.filter(tem_solicitacao_pendente=True)
    
    usuarios_paginados, page_numbers = paginar_itens(request, base_queryset, items_per_page=9)

    context = {
        'usuarios': usuarios_paginados,
        'paginated_object': usuarios_paginados,
        'page_numbers': page_numbers,
        'filtro_q': filtro_q,
        'filtro_permissao': filtro_permissao,
        'filtro_solicitacao': filtro_solicitacao,
        'total_usuarios': usuarios_paginados.paginator.count,
    }
    return render(request, 'gestao/listar_usuarios.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def editar_usuario_staff(request, user_id):
    usuario_alvo = get_object_or_404(User, id=user_id)
    old_is_staff = usuario_alvo.is_staff
    
    if request.method == 'POST':
        form = StaffUserForm(request.POST, instance=usuario_alvo)
        if form.is_valid():
            is_staff_novo = form.cleaned_data.get('is_staff')
            if usuario_alvo.is_superuser and not is_staff_novo:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Ação negada: Um Superusuário não pode ser removido do status "Membro da Equipe".'
                }, status=403)
            
            usuario_modificado = form.save()
            new_is_staff = usuario_modificado.is_staff

            if old_is_staff != new_is_staff:
                criar_log(
                    ator=request.user,
                    acao=LogAtividade.Acao.PERMISSOES_ALTERADAS,
                    alvo=usuario_alvo,
                    detalhes={
                        'usuario_alvo': usuario_alvo.username,
                        'de': 'Usuário Comum' if not old_is_staff else 'Membro da Equipe',
                        'para': 'Membro da Equipe' if new_is_staff else 'Usuário Comum'
                    }
                )

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

@login_required
@user_passes_test(is_staff_member)
@require_POST
def questoes_acoes_em_massa(request):
    try:
        data = json.loads(request.body)
        questao_ids = data.get('ids', [])
        action = data.get('action')

        if not questao_ids or not action:
            return JsonResponse({'status': 'error', 'message': 'IDs ou ação ausentes.'}, status=400)

        queryset = Questao.objects.filter(id__in=questao_ids)

        if action == 'delete':
            for questao in queryset:
                criar_log(
                    ator=request.user,
                    acao=LogAtividade.Acao.QUESTAO_DELETADA,
                    alvo=None,
                    detalhes={
                        'codigo_questao': questao.codigo,
                        'motivo': 'Ação de exclusão em massa'
                    }
                )

            count, _ = queryset.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': f' As questões selecionadas foram excluídas e a ação foi registrada no log com sucesso.'
            })
        else:
            return JsonResponse({'status': 'error', 'message': 'Ação inválida.'}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def promover_a_superuser(request, user_id):
    usuario_alvo = get_object_or_404(User, id=user_id)

    if usuario_alvo == request.user:
        return JsonResponse({
            'status': 'error',
            'message': 'Você não pode alterar suas próprias permissões de superusuário.'
        }, status=403)

    try:
        usuario_alvo.is_superuser = True
        usuario_alvo.is_staff = True
        usuario_alvo.save(update_fields=['is_superuser', 'is_staff'])
        
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.USUARIO_PROMOVIDO_SUPERUSER,
            alvo=usuario_alvo,
            detalhes={'usuario_alvo': usuario_alvo.username}
        )

        return JsonResponse({
            'status': 'success',
            'message': f'O usuário "{usuario_alvo.username}" foi promovido a Superusuário com sucesso.'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ocorreu um erro inesperado ao promover o usuário: {str(e)}'
        }, status=500)

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def despromover_de_superuser(request, user_id):
    usuario_alvo = get_object_or_404(User, id=user_id)

    if usuario_alvo == request.user:
        return JsonResponse({'status': 'error', 'message': 'Você não pode remover suas próprias permissões de superusuário.'}, status=403)

    if User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Não é possível remover as permissões do único superusuário do sistema.'}, status=403)

    try:
        usuario_alvo.is_superuser = False
        usuario_alvo.save(update_fields=['is_superuser'])
        
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.USUARIO_DESPROMOVIDO_SUPERUSER,
            alvo=usuario_alvo,
            detalhes={'usuario_alvo': usuario_alvo.username}
        )

        return JsonResponse({
            'status': 'success',
            'message': f'O usuário "{usuario_alvo.username}" não é mais um Superusuário. Ele ainda é um Membro da Equipe.'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro inesperado: {str(e)}'}, status=500)

@login_required
@user_passes_test(is_staff_member)
def listar_solicitacoes_exclusao(request):
    solicitacoes_list = SolicitacaoExclusao.objects.filter(
        status=SolicitacaoExclusao.Status.PENDENTE
    ).select_related('usuario_a_ser_excluido', 'solicitado_por').order_by('-data_solicitacao')

    solicitacoes_paginadas, page_numbers = paginar_itens(request, solicitacoes_list, items_per_page=10)

    context = {
        'solicitacoes': solicitacoes_paginadas,
        'paginated_object': solicitacoes_paginadas,
        'page_numbers': page_numbers,
        'total_solicitacoes': solicitacoes_paginadas.paginator.count,
    }
    return render(request, 'gestao/listar_solicitacoes_exclusao.html', context)

@login_required
@user_passes_test(is_staff_member)
@require_POST
def deletar_questao(request, questao_id):
    questao = get_object_or_404(Questao, id=questao_id)
    
    try:
        questao_codigo = questao.codigo

        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.QUESTAO_DELETADA,
            alvo=None, # Objeto será deletado
            detalhes={'codigo_questao': questao.codigo}
        )

        questao.delete()
        return JsonResponse({
            'status': 'success',
            'message': f'A questão "{questao_codigo}" foi excluída com sucesso.',
            'deleted_questao_id': questao_id
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Não foi possível excluir a questão. Erro: {str(e)}'
        }, status=500)

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def sugerir_exclusao_usuario(request, user_id):
    usuario_alvo = get_object_or_404(User, id=user_id)
    form = ExclusaoUsuarioForm(request.POST)

    if usuario_alvo.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Membros da equipe não podem sugerir a exclusão de superusuários.'}, status=403)
    if SolicitacaoExclusao.objects.filter(usuario_a_ser_excluido=usuario_alvo, status=SolicitacaoExclusao.Status.PENDENTE).exists():
        return JsonResponse({'status': 'error', 'message': 'Já existe uma solicitação de exclusão pendente para este usuário.'}, status=400)

    form.fields['justificativa'].required = True
        
    if form.is_valid():
        motivo_predefinido_chave = form.cleaned_data['motivo_predefinido']
        motivo_predefinido_texto = dict(form.fields['motivo_predefinido'].choices)[motivo_predefinido_chave]
        justificativa = form.cleaned_data['justificativa']
        motivo_completo = f"Motivo: {motivo_predefinido_texto}\n\nJustificativa: {justificativa}"

        solicitacao = SolicitacaoExclusao.objects.create(
            usuario_a_ser_excluido=usuario_alvo,
            solicitado_por=request.user,
            motivo=motivo_completo
        )
        
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_CRIADA,
            alvo=solicitacao,
            detalhes={'usuario_alvo': usuario_alvo.username}
        )
        
        return JsonResponse({'status': 'success', 'message': 'Sua sugestão de exclusão foi enviada para revisão por um superusuário.'})
    
    return JsonResponse({'status': 'error', 'message': 'Por favor, corrija os erros abaixo.', 'field_errors': form.errors}, status=400)

@login_required
@user_passes_test(is_staff_member)
@require_POST
def cancelar_solicitacao_exclusao(request, solicitacao_id):
    try:
        solicitacao = get_object_or_404(
            SolicitacaoExclusao, 
            id=solicitacao_id, 
            solicitado_por=request.user, 
            status=SolicitacaoExclusao.Status.PENDENTE
        )
        
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_CANCELADA,
            alvo=solicitacao,
            detalhes={'usuario_alvo': solicitacao.usuario_a_ser_excluido.username}
        )

        solicitacao.delete()

        return JsonResponse({
            'status': 'success',
            'message': 'Sua solicitação de exclusão foi cancelada com sucesso.',
            'solicitacao_id': solicitacao_id
        })
    except SolicitacaoExclusao.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Solicitação não encontrada ou você não tem permissão para cancelá-la.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro: {str(e)}'}, status=500)

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def aprovar_solicitacao_exclusao(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoExclusao, id=solicitacao_id, status=SolicitacaoExclusao.Status.PENDENTE)
    usuario_a_deletar = solicitacao.usuario_a_ser_excluido

    if User.objects.filter(is_superuser=True, is_active=True).count() <= 1 and usuario_a_deletar.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Não é possível aprovar a exclusão do único superusuário.'}, status=403)

    email_alvo = usuario_a_deletar.email
    username_alvo = usuario_a_deletar.username
    motivo_texto = solicitacao.motivo
    message = ""

    try:
        if email_alvo:
            try:
                enviar_email_com_template(
                    request,
                    subject='Sua conta na plataforma Raio-X da Aprovação foi removida',
                    template_name='gestao/email_conta_excluida.html',
                    context={'user': usuario_a_deletar, 'motivo_texto': motivo_texto},
                    recipient_list=[email_alvo]
                )
                message = f'A solicitação foi aprovada, o usuário "{username_alvo}" foi excluído e notificado.'
            except Exception as e:
                message = f'A solicitação foi aprovada e o usuário "{username_alvo}" foi excluído, mas o envio de e-mail falhou: {e}'
        else:
            message = f'A solicitação foi aprovada e o usuário "{username_alvo}" foi excluído. (Sem e-mail para notificar).'

        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_APROVADA,
            alvo=solicitacao,
            detalhes={
                'usuario_excluido': usuario_a_deletar.username,
                'solicitado_por': solicitacao.solicitado_por.username
            }
        )
        
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.USUARIO_DELETADO,
            alvo=None,
            detalhes={
                'usuario_deletado': usuario_a_deletar.username,
                'motivo': f'Aprovação da solicitação #{solicitacao.id}'
            }
        )

        solicitacao.status = SolicitacaoExclusao.Status.APROVADO
        solicitacao.revisado_por = request.user
        solicitacao.data_revisao = timezone.now()
        solicitacao.save()
        
        usuario_a_deletar.delete()

        return JsonResponse({'status': 'success', 'message': message, 'solicitacao_id': solicitacao_id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Ocorreu um erro inesperado: {str(e)}'}, status=500)

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def deletar_usuario(request, user_id):
    usuario_alvo = get_object_or_404(User, id=user_id)
    form = ExclusaoUsuarioForm(request.POST)

    if usuario_alvo == request.user:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Você não pode excluir sua própria conta.'}, status=403)
    if usuario_alvo.is_superuser and User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Não é possível excluir o único superusuário do sistema.'}, status=403)

    if form.is_valid():
        motivo_predefinido_chave = form.cleaned_data['motivo_predefinido']
        motivo_predefinido_texto = dict(form.fields['motivo_predefinido'].choices)[motivo_predefinido_chave]
        justificativa = form.cleaned_data.get('justificativa', '')
        
        motivo_final_para_email = f"{motivo_predefinido_texto}"
        if justificativa:
            motivo_final_para_email += f" (Detalhes: {justificativa})"
            
        email_alvo = usuario_alvo.email
        username_alvo = usuario_alvo.username

        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.USUARIO_DELETADO,
            alvo=None,
            detalhes={
                'usuario_deletado': usuario_alvo.username,
                'motivo': motivo_final_para_email
            }
        )

        message = ""
        if email_alvo:
            try:
                enviar_email_com_template(
                    request,
                    subject='Sua conta na plataforma Raio-X da Aprovação foi removida',
                    template_name='gestao/email_conta_excluida.html',
                    context={'user': usuario_alvo, 'motivo_texto': motivo_final_para_email},
                    recipient_list=[email_alvo]
                )
                message = f'O usuário "{username_alvo}" foi excluído e notificado por e-mail com sucesso.'
            except Exception as e:
                message = f'O usuário "{username_alvo}" foi excluído, mas ocorreu um erro ao enviar o e-mail: {e}'
        else:
            message = f'O usuário "{username_alvo}" foi excluído. (Nenhuma notificação foi enviada por falta de e-mail).'
        
        usuario_alvo.delete()

        return JsonResponse({'status': 'success', 'message': message, 'deleted_user_id': user_id })
    else:
        return JsonResponse({'status': 'error', 'message': 'Por favor, corrija os erros abaixo.', 'field_errors': form.errors}, status=400)

@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def rejeitar_solicitacao_exclusao(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoExclusao, id=solicitacao_id, status=SolicitacaoExclusao.Status.PENDENTE)
    
    try:
        criar_log(
            ator=request.user,
            acao=LogAtividade.Acao.SOLICITACAO_EXCLUSAO_REJEITADA,
            alvo=solicitacao,
            detalhes={
                'usuario_alvo': solicitacao.usuario_a_ser_excluido.username,
                'solicitado_por': solicitacao.solicitado_por.username
            }
        )

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

def criar_log(ator, acao, alvo=None, detalhes={}):
    """
    Cria uma nova entrada no Registro de Atividades de forma centralizada.
    """
    LogAtividade.objects.create(
        ator=ator,
        acao=acao,
        alvo=alvo,
        detalhes=detalhes
    )
    
@login_required
@user_passes_test(lambda u: u.is_superuser)
def listar_logs_atividade(request):
    filtro_q = request.GET.get('q', '').strip()
    filtro_acao = request.GET.get('acao', '')
    filtro_data_inicio = request.GET.get('data_inicio', '')
    filtro_data_fim = request.GET.get('data_fim', '')

    logs_list = LogAtividade.objects.select_related('ator').all()

    if filtro_q:
        logs_list = logs_list.filter(Q(ator__username__icontains=filtro_q) | Q(ator__email__icontains=filtro_q))
    if filtro_acao:
        logs_list = logs_list.filter(acao=filtro_acao)
    if filtro_data_inicio:
        try:
            data_inicio_obj = datetime.strptime(filtro_data_inicio, '%Y-%m-%d')
            logs_list = logs_list.filter(data_criacao__gte=data_inicio_obj)
        except (ValueError, TypeError): pass
    if filtro_data_fim:
        try:
            data_fim_obj = datetime.strptime(filtro_data_fim, '%Y-%m-%d') + timedelta(days=1)
            logs_list = logs_list.filter(data_criacao__lt=data_fim_obj)
        except (ValueError, TypeError): pass

    logs_paginados, page_numbers = paginar_itens(request, logs_list, 20)
    
    context = {
        'logs': logs_paginados,
        'paginated_object': logs_paginados,
        'page_numbers': page_numbers,
        'filtro_q': filtro_q,
        'filtro_acao': filtro_acao,
        'filtro_data_inicio': filtro_data_inicio,
        'filtro_data_fim': filtro_data_fim,
        'acao_choices': LogAtividade.Acao.choices,
    }
    return render(request, 'gestao/listar_logs_atividade.html', context)

@require_POST
@user_passes_test(lambda u: u.is_superuser)
def deletar_log_atividade(request, log_id):
    log = get_object_or_404(LogAtividade, id=log_id)
    if log.ator == request.user:
        return JsonResponse({'status': 'error', 'message': 'Ação negada: Você não pode excluir seus próprios registros.'}, status=403)
    try:
        log.delete()
        return JsonResponse({'status': 'success', 'message': 'Registro excluído.', 'deleted_log_id': log_id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_POST
@user_passes_test(lambda u: u.is_superuser)
def logs_acoes_em_massa(request):
    try:
        data = json.loads(request.body)
        log_ids = data.get('ids', [])
        action = data.get('action')

        if not log_ids or not action:
            return JsonResponse({'status': 'error', 'message': 'IDs ou ação ausentes.'}, status=400)

        if action == 'delete':
            queryset = LogAtividade.objects.filter(id__in=log_ids).exclude(ator=request.user)
            
            count, _ = queryset.delete()

            if count < len(log_ids):
                message = f'{count} registro(s) foram excluídos. Os seus próprios registros não foram alterados.'
            else:
                message = f'{count} registro(s) foram excluídos com sucesso.'

            return JsonResponse({ 'status': 'success', 'message': message })
        else:
            return JsonResponse({'status': 'error', 'message': 'Ação inválida.'}, status=400)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)