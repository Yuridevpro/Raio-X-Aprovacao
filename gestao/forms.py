# gestao/forms.py

from django import forms
from django.contrib.auth.models import User
from .models import SolicitacaoExclusao
# a. IMPORTANDO O NOVO MODELO DE CONFIGURAÇÕES
from gamificacao.models import Conquista, GamificationSettings
from simulados.models import Simulado, StatusSimulado, NivelDificuldade
from questoes.models import Questao, Disciplina, Banca, Assunto, Instituicao
from gamificacao.models import Conquista, Avatar, Borda, Banner


from gamificacao.models import Conquista, GamificationSettings
# ...

class GamificationSettingsForm(forms.ModelForm):
    class Meta:
        model = GamificationSettings
        fields = '__all__'
        widgets = {
            'xp_por_acerto': forms.NumberInput(attrs={'class': 'form-control'}),
            'xp_por_erro': forms.NumberInput(attrs={'class': 'form-control'}),
            'xp_acerto_primeira_vez': forms.NumberInput(attrs={'class': 'form-control'}),
            'xp_acerto_redencao': forms.NumberInput(attrs={'class': 'form-control'}),
            'xp_bonus_meta_diaria': forms.NumberInput(attrs={'class': 'form-control'}),
            'meta_diaria_questoes': forms.NumberInput(attrs={'class': 'form-control'}),
            'acertos_consecutivos_para_bonus': forms.NumberInput(attrs={'class': 'form-control'}),
            'bonus_multiplicador_acertos_consecutivos': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'habilitar_teto_xp_diario': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'teto_xp_diario': forms.NumberInput(attrs={'class': 'form-control'}),
            'cooldown_mesma_questao_horas': forms.NumberInput(attrs={'class': 'form-control'}),
            'tempo_minimo_entre_respostas_segundos': forms.NumberInput(attrs={'class': 'form-control'}),
        }


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


# =======================================================================
# FORMULÁRIO DE CONQUISTA ATUALIZADO PARA O PAINEL DE GESTÃO
# =======================================================================
class ConquistaForm(forms.ModelForm):
    class Meta:
        model = Conquista
        fields = ['nome', 'chave', 'descricao', 'icone', 'cor']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'chave': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: STREAK_7_DIAS'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: fas fa-fire'}),
            'cor': forms.TextInput(attrs={'class': 'form-control', 'type': 'color', 'style': 'width: 100px;'}),
        }
        help_texts = {
            'chave': 'Este é o identificador único usado pelo sistema. NÃO MUDE após criado, pois pode quebrar a lógica de atribuição.',
            'icone': 'Use classes do Font Awesome (ex: "fas fa-trophy").',
        }
        
        
class SimuladoForm(forms.ModelForm):
    class Meta:
        model = Simulado
        fields = ['nome', 'questoes']

    questoes = forms.ModelMultipleChoiceField(
        queryset=Questao.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'id': 'tom-select-questoes'}),
        label="Questões do Simulado",
        required=False
    )
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
        queryset=Assunto.objects.none(),
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

    def __init__(self, *args, **kwargs):
        fields_to_show = kwargs.pop('fields_to_show', None)
        super().__init__(*args, **kwargs)

        if 'disciplina' in self.data:
            try:
                disciplina_id = int(self.data.get('disciplina'))
                self.fields['assunto'].queryset = Assunto.objects.filter(disciplina_id=disciplina_id).order_by('nome')
            except (ValueError, TypeError):
                pass
        
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
        # =======================================================================
        # INÍCIO DA CORREÇÃO: Adicionando o campo 'dificuldade'
        # =======================================================================
        fields = ['nome', 'status', 'dificuldade']
        # =======================================================================
        # FIM DA CORREÇÃO
        # =======================================================================
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            # =======================================================================
            # INÍCIO DA CORREÇÃO: Widget para o novo campo
            # =======================================================================
            'dificuldade': forms.Select(attrs={'class': 'form-select'}),
            # =======================================================================
            # FIM DA CORREÇÃO
            # =======================================================================
        }
        
class SimuladoWizardForm(forms.Form):
    """ Formulário para a primeira etapa da criação de um simulado. """
    nome = forms.CharField(
        label="Nome do Simulado",
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Simulado de Direito Constitucional - FGV'})
    )
    # =======================================================================
    # INÍCIO DA CORREÇÃO: Adicionando o campo de dificuldade na criação
    # =======================================================================
    dificuldade = forms.ChoiceField(
        choices=NivelDificuldade.choices,
        label="Nível de Dificuldade",
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial=NivelDificuldade.MEDIO,
        required=True
    )
    # =======================================================================
    # FIM DA CORREÇÃO
    # =======================================================================
    disciplinas = forms.ModelMultipleChoiceField(
        queryset=Disciplina.objects.all().order_by('nome'),
        widget=forms.SelectMultiple(),
        required=False
    )
    assuntos = forms.ModelMultipleChoiceField(
        queryset=Assunto.objects.none(),
        widget=forms.SelectMultiple(),
        required=False
    )
    bancas = forms.ModelMultipleChoiceField(
        queryset=Banca.objects.all().order_by('nome'),
        widget=forms.SelectMultiple(),
        required=False
    )
    instituicoes = forms.ModelMultipleChoiceField(
        queryset=Instituicao.objects.all().order_by('nome'),
        widget=forms.SelectMultiple(),
        required=False
    )
    anos = forms.MultipleChoiceField(
        choices=[],
        widget=forms.SelectMultiple(),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        anos_disponiveis = Questao.objects.exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano')
        self.fields['anos'].choices = [(ano, ano) for ano in anos_disponiveis]

        if 'disciplinas' in self.data:
            try:
                disciplina_ids = self.data.getlist('disciplinas')
                self.fields['assuntos'].queryset = Assunto.objects.filter(disciplina_id__in=disciplina_ids).order_by('nome')
            except (ValueError, TypeError):
                pass

# c. FORMULÁRIOS DE RECOMPENSAS ATUALIZADOS
class RecompensaBaseForm(forms.ModelForm):
    """Formulário base para compartilhar campos entre Avatar, Borda e Banner."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['conquista_necessaria'].queryset = Conquista.objects.all().order_by('nome')
        self.fields['conquista_necessaria'].required = False

class AvatarForm(RecompensaBaseForm):
    class Meta:
        model = Avatar
        fields = ['nome', 'descricao', 'imagem', 'raridade', 'tipo_desbloqueio', 'nivel_necessario', 'conquista_necessaria']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Desbloqueado ao atingir o Nível 10'}),
            'imagem': forms.FileInput(attrs={'class': 'form-control'}),
            'raridade': forms.Select(attrs={'class': 'form-select'}),
            'tipo_desbloqueio': forms.Select(attrs={'class': 'form-select'}),
            'nivel_necessario': forms.NumberInput(attrs={'class': 'form-control'}),
            'conquista_necessaria': forms.Select(attrs={'class': 'form-select'}),
        }

class BordaForm(RecompensaBaseForm):
    class Meta:
        model = Borda
        fields = ['nome', 'descricao', 'imagem', 'raridade', 'tipo_desbloqueio', 'nivel_necessario', 'conquista_necessaria']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Desbloqueado pela conquista "Mão Calibrada"'}),
            'imagem': forms.FileInput(attrs={'class': 'form-control'}),
            'raridade': forms.Select(attrs={'class': 'form-select'}),
            'tipo_desbloqueio': forms.Select(attrs={'class': 'form-select'}),
            'nivel_necessario': forms.NumberInput(attrs={'class': 'form-control'}),
            'conquista_necessaria': forms.Select(attrs={'class': 'form-select'}),
        }

# gestao/forms.py

# gestao/forms.py

class BannerForm(RecompensaBaseForm):
    class Meta:
        model = Banner
        # MUDANÇA: Removidos os campos 'background_position' e 'background_size'.
        fields = ['nome', 'descricao', 'imagem', 'raridade', 'tipo_desbloqueio', 'nivel_necessario', 'conquista_necessaria']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Recompensa de Fim de Ano'}),
            'imagem': forms.FileInput(attrs={'class': 'form-control'}), # O input de arquivo padrão
            'raridade': forms.Select(attrs={'class': 'form-select'}),
            'tipo_desbloqueio': forms.Select(attrs={'class': 'form-select'}),
            'nivel_necessario': forms.NumberInput(attrs={'class': 'form-control'}),
            'conquista_necessaria': forms.Select(attrs={'class': 'form-select'}),
        }