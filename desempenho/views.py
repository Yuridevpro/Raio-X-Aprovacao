# desempenho/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from pratica.models import RespostaUsuario
from questoes.models import Disciplina, Banca
import json

@login_required
def dashboard(request):
    usuario = request.user

    # --- Estatísticas Gerais ---
    respostas = RespostaUsuario.objects.filter(usuario=usuario)
    total_respondidas = respostas.count()
    total_acertos = respostas.filter(foi_correta=True).count()
    total_erros = total_respondidas - total_acertos
    
    percentual_acerto_geral = (total_acertos / total_respondidas * 100) if total_respondidas > 0 else 0

    # --- Desempenho por Disciplina ---
    desempenho_disciplina = Disciplina.objects.filter(
        questao__respostausuario__usuario=usuario
    ).annotate(
        total=Count('questao'),
        acertos=Count('questao', filter=Q(questao__respostausuario__foi_correta=True))
    ).order_by('-total')

    # --- INÍCIO DA CORREÇÃO ---
    # Adicionando o cálculo do percentual diretamente no objeto
    for d in desempenho_disciplina:
        d.percentual_acerto = (d.acertos / d.total * 100) if d.total > 0 else 0
    # --- FIM DA CORREÇÃO ---

    labels_disciplina = [d.nome for d in desempenho_disciplina]
    data_acertos_disciplina = [d.acertos for d in desempenho_disciplina]
    data_erros_disciplina = [(d.total - d.acertos) for d in desempenho_disciplina]

    # --- Desempenho por Banca ---
    desempenho_banca = Banca.objects.filter(
        questao__respostausuario__usuario=usuario
    ).annotate(
        total=Count('questao'),
        acertos=Count('questao', filter=Q(questao__respostausuario__foi_correta=True))
    ).order_by('-total')

    # --- INÍCIO DA CORREÇÃO ---
    # Adicionando o cálculo do percentual diretamente no objeto
    for b in desempenho_banca:
        b.percentual_acerto = (b.acertos / b.total * 100) if b.total > 0 else 0
    # --- FIM DA CORREÇÃO ---

    labels_banca = [b.nome for b in desempenho_banca]
    data_acertos_banca = [b.acertos for b in desempenho_banca]

    context = {
        'total_respondidas': total_respondidas,
        'total_acertos': total_acertos,
        'total_erros': total_erros,
        'percentual_acerto_geral': round(percentual_acerto_geral, 2),
        'desempenho_disciplina': desempenho_disciplina,
        'desempenho_banca': desempenho_banca,
        'labels_disciplina': json.dumps(labels_disciplina),
        'data_acertos_disciplina': json.dumps(data_acertos_disciplina),
        'data_erros_disciplina': json.dumps(data_erros_disciplina),
        'labels_banca': json.dumps(labels_banca),
        'data_acertos_banca': json.dumps(data_acertos_banca),
    }

    return render(request, 'desempenho/dashboard.html', context)