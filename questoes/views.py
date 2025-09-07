# questoes/views.py

from django.http import JsonResponse
from .models import Assunto

def get_assuntos_por_disciplina(request):
    """
    View de API centralizada para buscar assuntos de uma ou mais disciplinas.
    """
    disciplina_ids = request.GET.getlist('disciplina_ids[]')
    if not disciplina_ids:
        return JsonResponse({'assuntos': []})

    assuntos = Assunto.objects.filter(disciplina_id__in=disciplina_ids).values(
        'id', 'nome', 'disciplina__nome'
    ).order_by('disciplina__nome', 'nome')
    
    return JsonResponse({'assuntos': list(assuntos)})