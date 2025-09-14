# gestao/forms.py (ARQUIVO CORRIGIDO)

from django import forms
from django.contrib.auth.models import User
from .models import SolicitacaoExclusao

# =======================================================================
# INÍCIO DA CORREÇÃO: Imports agora apontam para os apps corretos
# =======================================================================
from gamificacao.models import Conquista
from simulados.models import Simulado

from questoes.models import Questao, Disciplina, Banca, Assunto, Instituicao

# =======================================================================
# FIM DA CORREÇÃO
# =======================================================================

class StaffUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'is_staff']
        widgets = {
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }
        help_texts = {
            'is_staff': "Marque esta opção para conceder acesso ao painel de gestão a este usuário."
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].disabled = True
        self.fields['email'].disabled = True

class ExclusaoUsuarioForm(forms.Form):
    MOTIVO_CHOICES = [
        ('', '---------'),
        ('TERMOS_DE_SERVICO', 'Violação dos Termos de Serviço'),
        ('CONDUTA_INADEQUADA', 'Conduta Inadequada / Abusiva'),
        ('INATIVIDADE', 'Conta Inativa por Longo Período'),
        ('SEGURANCA', 'Atividade Suspeita / Risco de Segurança'),
        ('SOLICITACAO_USUARIO', 'A Pedido do Próprio Usuário'),
        ('OUTRO', 'Outro (detalhar abaixo)'),
    ]
    motivo_predefinido = forms.ChoiceField(
        choices=MOTIVO_CHOICES,
        label="Selecione o motivo principal",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    justificativa = forms.CharField(
        label="Justificativa Detalhada",
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'form-control',
            'placeholder': 'Forneça detalhes específicos sobre o motivo da exclusão.'
        }),
        required=False
    )

class ConquistaForm(forms.ModelForm):
    class Meta:
        model = Conquista
        fields = ['nome', 'chave', 'descricao', 'icone', 'cor']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'chave': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: STREAK_7_DIAS'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: fas fa-fire'}),
            'cor': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }
        help_texts = {
            'chave': 'Este é o identificador único usado pelo sistema. Não mude após criado.',
            'icone': 'Use classes do Font Awesome (ex: "fas fa-trophy").',
        }

class SimuladoForm(forms.ModelForm):
    # =======================================================================
    # INÍCIO DA ADIÇÃO: Classe Meta para resolver o erro
    # =======================================================================
    class Meta:
        model = Simulado
        # O ModelForm irá gerar automaticamente o campo 'nome'.
        # O campo 'questoes' já está definido abaixo e será usado em vez do padrão.
        fields = ['nome', 'questoes']
    # =======================================================================
    # FIM DA ADIÇÃO
    # =======================================================================

    # Campos para a funcionalidade de EDIÇÃO (existente) - Lógica Mantida
    questoes = forms.ModelMultipleChoiceField(
        queryset=Questao.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'id': 'tom-select-questoes'}),
        label="Questões do Simulado",
        required=False
    )

    # Campos para a funcionalidade de CRIAÇÃO (nova) - Lógica Mantida
    banca = forms.ModelChoiceField(
        queryset=Banca.objects.all().order_by('nome'),
        label="Banca",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    disciplina = forms.ModelChoiceField(
        queryset=Disciplina.objects.all().order_by('nome'),
        label="Disciplina (opcional)",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    assunto = forms.ModelChoiceField(
        queryset=Assunto.objects.none(),  # Inicia vazio, será populado por JS
        label="Assunto",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    instituicao = forms.ModelChoiceField(
        queryset=Instituicao.objects.all().order_by('nome'),
        label="Instituição (opcional)",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )

    # Lógica de inicialização existente é totalmente preservada
    def __init__(self, *args, **kwargs):
        fields_to_show = kwargs.pop('fields_to_show', None)
        super().__init__(*args, **kwargs)

        # Lógica para popular dinamicamente os assuntos
        if 'disciplina' in self.data:
            try:
                disciplina_id = int(self.data.get('disciplina'))
                self.fields['assunto'].queryset = Assunto.objects.filter(disciplina_id=disciplina_id).order_by('nome')
            except (ValueError, TypeError):
                pass
        
        # Lógica existente para mostrar/esconder campos
        if fields_to_show is not None:
            allowed = set(fields_to_show)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

class SimuladoMetaForm(forms.ModelForm):
    """
    Formulário enxuto para editar os metadados de um simulado via modal.
    """
    class Meta:
        model = Simulado
        fields = ['nome', 'status']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        
        
class SimuladoWizardForm(forms.Form):
    """ Formulário para a primeira etapa da criação de um simulado. """
    nome = forms.CharField(
        label="Nome do Simulado",
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Simulado de Direito Constitucional - FGV'})
    )
    disciplinas = forms.ModelMultipleChoiceField(
        queryset=Disciplina.objects.all().order_by('nome'),
        widget=forms.SelectMultiple(attrs={'class': 'form-select tom-select'}),
        required=False
    )
    # =======================================================================
    # INÍCIO DA ADIÇÃO: Campo de filtro para Assunto
    # =======================================================================
    assuntos = forms.ModelMultipleChoiceField(
        queryset=Assunto.objects.none(), # Inicia vazio, será populado por JS
        widget=forms.SelectMultiple(attrs={'class': 'form-select tom-select'}),
        required=False
    )
    # =======================================================================
    # FIM DA ADIÇÃO
    # =======================================================================
    bancas = forms.ModelMultipleChoiceField(
        queryset=Banca.objects.all().order_by('nome'),
        widget=forms.SelectMultiple(attrs={'class': 'form-select tom-select'}),
        required=False
    )
    instituicoes = forms.ModelMultipleChoiceField(
        queryset=Instituicao.objects.all().order_by('nome'),
        widget=forms.SelectMultiple(attrs={'class': 'form-select tom-select'}),
        required=False
    )
    anos = forms.MultipleChoiceField(
        choices=[],
        widget=forms.SelectMultiple(attrs={'class': 'form-select tom-select'}),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        anos_disponiveis = Questao.objects.exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano')
        self.fields['anos'].choices = [(ano, ano) for ano in anos_disponiveis]

        # Popula o queryset de assuntos se disciplinas foram enviadas (caso de erro no POST)
        if 'disciplinas' in self.data:
            try:
                disciplina_ids = self.data.getlist('disciplinas')
                self.fields['assuntos'].queryset = Assunto.objects.filter(disciplina_id__in=disciplina_ids).order_by('nome')
            except (ValueError, TypeError):
                pass