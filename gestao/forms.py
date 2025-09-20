# gestao/forms.py (ARQUIVO CORRIGIDO E FINALIZADO)

from django import forms
from django.contrib.auth.models import User
from .models import SolicitacaoExclusao
from gamificacao.models import (
    Conquista, GamificationSettings, Campanha, Avatar, Borda, Banner,
    CondicaoVolumeQuestoes, CondicaoStreak, TrilhaDeConquistas
)
from simulados.models import Simulado, StatusSimulado, NivelDificuldade
from questoes.models import Questao, Disciplina, Banca, Assunto, Instituicao
import json
from gamificacao.models import TipoCondicao


# =======================================================================
# FORMULÁRIOS DE CONFIGURAÇÃO E GESTÃO GERAL
# =======================================================================
class GamificationSettingsForm(forms.ModelForm):
    class Meta:
        model = GamificationSettings
        fields = '__all__'
        widgets = {
            # XP por Questões
            'xp_por_acerto': forms.NumberInput(attrs={'class': 'form-control'}),
            'xp_por_erro': forms.NumberInput(attrs={'class': 'form-control'}),
            'xp_acerto_primeira_vez': forms.NumberInput(attrs={'class': 'form-control'}),
            'xp_acerto_redencao': forms.NumberInput(attrs={'class': 'form-control'}),
            # Bônus e Metas
            'acertos_consecutivos_para_bonus': forms.NumberInput(attrs={'class': 'form-control'}),
            'bonus_multiplicador_acertos_consecutivos': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'xp_bonus_meta_diaria': forms.NumberInput(attrs={'class': 'form-control'}),
            'meta_diaria_questoes': forms.NumberInput(attrs={'class': 'form-control'}),
            # Segurança e Anti-Farming
            'habilitar_teto_xp_diario': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'teto_xp_diario': forms.NumberInput(attrs={'class': 'form-control'}),
            'cooldown_mesma_questao_horas': forms.NumberInput(attrs={'class': 'form-control'}),
            'tempo_minimo_entre_respostas_segundos': forms.NumberInput(attrs={'class': 'form-control'}),
            'cooldown_mesmo_simulado_horas': forms.NumberInput(attrs={'class': 'form-control'}),
            # XP por Simulados
            'usar_xp_dinamico_simulado': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'xp_dinamico_considera_erros': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'multiplicador_xp_simulado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'xp_base_simulado_concluido': forms.NumberInput(attrs={'class': 'form-control'}),
            # CORREÇÃO: Adicionando os campos de Moedas que faltavam
            'moedas_por_acerto': forms.NumberInput(attrs={'class': 'form-control'}),
            'moedas_por_meta_diaria': forms.NumberInput(attrs={'class': 'form-control'}),
            'moedas_por_conclusao_simulado': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class StaffUserForm(forms.ModelForm):
    class Meta: model = User; fields = ['username', 'email', 'is_staff']; widgets = {'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'})}
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs); self.fields['username'].disabled = True; self.fields['email'].disabled = True

class ExclusaoUsuarioForm(forms.Form):
    MOTIVO_CHOICES = [('', '---------'), ('TERMOS_DE_SERVICO', 'Violação dos Termos de Serviço'), ('CONDUTA_INADEQUADA', 'Conduta Inadequada / Abusiva'), ('INATIVIDADE', 'Conta Inativa por Longo Período'), ('SEGURANCA', 'Atividade Suspeita / Risco de Segurança'), ('SOLICITACAO_USUARIO', 'A Pedido do Próprio Usuário'), ('OUTRO', 'Outro (detalhar abaixo)')]
    motivo_predefinido = forms.ChoiceField(choices=MOTIVO_CHOICES, label="Selecione o motivo principal", widget=forms.Select(attrs={'class': 'form-select'}), required=True)
    justificativa = forms.CharField(label="Justificativa Detalhada", widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Forneça detalhes específicos sobre o motivo da exclusão.'}), required=False)

# =======================================================================
# FORMULÁRIOS DE ITENS (SIMULADOS E RECOMPENSAS)
# =======================================================================
class SimuladoForm(forms.ModelForm):
    class Meta: model = Simulado; fields = ['nome', 'questoes']
    questoes = forms.ModelMultipleChoiceField(queryset=Questao.objects.all(), widget=forms.SelectMultiple(attrs={'class': 'form-control', 'id': 'tom-select-questoes'}), label="Questões do Simulado", required=False)
    banca = forms.ModelChoiceField(queryset=Banca.objects.all().order_by('nome'), label="Banca", widget=forms.Select(attrs={'class': 'form-select'}), required=True)
    disciplina = forms.ModelChoiceField(queryset=Disciplina.objects.all().order_by('nome'), label="Disciplina (opcional)", widget=forms.Select(attrs={'class': 'form-select'}), required=False)
    assunto = forms.ModelChoiceField(queryset=Assunto.objects.none(), label="Assunto", widget=forms.Select(attrs={'class': 'form-select'}), required=True)
    instituicao = forms.ModelChoiceField(queryset=Instituicao.objects.all().order_by('nome'), label="Instituição (opcional)", widget=forms.Select(attrs={'class': 'form-select'}), required=False)
    def __init__(self, *args, **kwargs):
        fields_to_show = kwargs.pop('fields_to_show', None)
        super().__init__(*args, **kwargs)
        if 'disciplina' in self.data:
            try: disciplina_id = int(self.data.get('disciplina')); self.fields['assunto'].queryset = Assunto.objects.filter(disciplina_id=disciplina_id).order_by('nome')
            except (ValueError, TypeError): pass
        if fields_to_show is not None:
            allowed = set(fields_to_show); existing = set(self.fields.keys())
            for field_name in existing - allowed: self.fields.pop(field_name)

class SimuladoMetaForm(forms.ModelForm):
    class Meta: model = Simulado; fields = ['nome', 'status', 'dificuldade']; widgets = {'nome': forms.TextInput(attrs={'class': 'form-control'}),'status': forms.Select(attrs={'class': 'form-select'}),'dificuldade': forms.Select(attrs={'class': 'form-select'})}

class SimuladoWizardForm(forms.Form):
    nome = forms.CharField(label="Nome do Simulado", max_length=200, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Simulado de Direito Constitucional - FGV'}))
    dificuldade = forms.ChoiceField(choices=NivelDificuldade.choices, label="Nível de Dificuldade", widget=forms.Select(attrs={'class': 'form-select'}), initial=NivelDificuldade.MEDIO, required=True)
    disciplinas = forms.ModelMultipleChoiceField(queryset=Disciplina.objects.all().order_by('nome'), widget=forms.SelectMultiple(), required=False)
    assuntos = forms.ModelMultipleChoiceField(queryset=Assunto.objects.none(), widget=forms.SelectMultiple(), required=False)
    bancas = forms.ModelMultipleChoiceField(queryset=Banca.objects.all().order_by('nome'), widget=forms.SelectMultiple(), required=False)
    instituicoes = forms.ModelMultipleChoiceField(queryset=Instituicao.objects.all().order_by('nome'), widget=forms.SelectMultiple(), required=False)
    anos = forms.MultipleChoiceField(choices=[], widget=forms.SelectMultiple(), required=False)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        anos_disponiveis = Questao.objects.exclude(ano__isnull=True).values_list('ano', flat=True).distinct().order_by('-ano')
        self.fields['anos'].choices = [(ano, ano) for ano in anos_disponiveis]
        if 'disciplinas' in self.data:
            try: disciplina_ids = self.data.getlist('disciplinas'); self.fields['assuntos'].queryset = Assunto.objects.filter(disciplina_id__in=disciplina_ids).order_by('nome')
            except (ValueError, TypeError): pass

class RecompensaBaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'conquista_necessaria' in self.fields:
            self.fields['conquista_necessaria'].queryset = Conquista.objects.all().order_by('nome')
            self.fields['conquista_necessaria'].required = False
        if 'preco_moedas' in self.fields:
            self.fields['preco_moedas'].required = False

    def clean(self):
        cleaned_data = super().clean()
        tipo_desbloqueio = cleaned_data.get('tipo_desbloqueio')
        if tipo_desbloqueio == 'LOJA' and cleaned_data.get('preco_moedas', 0) <= 0: self.add_error('preco_moedas', 'Se o item é comprável, o preço deve ser maior que zero.')
        if tipo_desbloqueio == 'NIVEL' and not cleaned_data.get('nivel_necessario'): self.add_error('nivel_necessario', 'Este campo é obrigatório para desbloqueio por nível.')
        if tipo_desbloqueio == 'CONQUISTA' and not cleaned_data.get('conquista_necessaria'): self.add_error('conquista_necessaria', 'Este campo é obrigatório para desbloqueio por conquista.')
        return cleaned_data


class AvatarForm(RecompensaBaseForm):
    class Meta: model = Avatar; fields = ['nome', 'descricao', 'imagem', 'raridade', 'tipo_desbloqueio', 'nivel_necessario', 'conquista_necessaria', 'preco_moedas']; widgets = {'nome': forms.TextInput(attrs={'class': 'form-control'}),'descricao': forms.TextInput(attrs={'class': 'form-control'}),'imagem': forms.FileInput(attrs={'class': 'form-control'}),'raridade': forms.Select(attrs={'class': 'form-select'}),'tipo_desbloqueio': forms.Select(attrs={'class': 'form-select'}),'nivel_necessario': forms.NumberInput(attrs={'class': 'form-control'}),'conquista_necessaria': forms.Select(attrs={'class': 'form-select'}),'preco_moedas': forms.NumberInput(attrs={'class': 'form-control'})}
class BordaForm(RecompensaBaseForm):
    class Meta: model = Borda; fields = ['nome', 'descricao', 'imagem', 'raridade', 'tipo_desbloqueio', 'nivel_necessario', 'conquista_necessaria', 'preco_moedas']; widgets = {'nome': forms.TextInput(attrs={'class': 'form-control'}),'descricao': forms.TextInput(attrs={'class': 'form-control'}),'imagem': forms.FileInput(attrs={'class': 'form-control'}),'raridade': forms.Select(attrs={'class': 'form-select'}),'tipo_desbloqueio': forms.Select(attrs={'class': 'form-select'}),'nivel_necessario': forms.NumberInput(attrs={'class': 'form-control'}),'conquista_necessaria': forms.Select(attrs={'class': 'form-select'}),'preco_moedas': forms.NumberInput(attrs={'class': 'form-control'})}
class BannerForm(RecompensaBaseForm):
    class Meta: model = Banner; fields = ['nome', 'descricao', 'imagem', 'raridade', 'tipo_desbloqueio', 'nivel_necessario', 'conquista_necessaria', 'preco_moedas']; widgets = {'nome': forms.TextInput(attrs={'class': 'form-control'}),'descricao': forms.TextInput(attrs={'class': 'form-control'}),'imagem': forms.FileInput(attrs={'class': 'form-control'}),'raridade': forms.Select(attrs={'class': 'form-select'}),'tipo_desbloqueio': forms.Select(attrs={'class': 'form-select'}),'nivel_necessario': forms.NumberInput(attrs={'class': 'form-control'}),'conquista_necessaria': forms.Select(attrs={'class': 'form-select'}),'preco_moedas': forms.NumberInput(attrs={'class': 'form-control'})}

# =======================================================================
# FORMULÁRIOS DE CAMPANHAS, TRILHAS E CONQUISTAS
# =======================================================================
class CampanhaForm(forms.ModelForm):
    class Meta:
        model = Campanha
        fields = ['nome', 'ativo', 'gatilho', 'data_inicio', 'data_fim', 'tipo_recorrencia']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
            'gatilho': forms.Select(attrs={'class': 'form-select', 'id': 'id_gatilho_select'}),
            'data_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'data_fim': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'tipo_recorrencia': forms.Select(attrs={'class': 'form-select'}),
        }

class TrilhaDeConquistasForm(forms.ModelForm):
    class Meta:
        model = TrilhaDeConquistas
        fields = ['nome', 'descricao', 'icone', 'ordem']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: fas fa-road'}),
            'ordem': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ConquistaForm(forms.ModelForm):
    recompensa_xp = forms.IntegerField(label="XP Extra", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    recompensa_moedas = forms.IntegerField(label="Moedas Extras", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    recompensa_avatares = forms.ModelMultipleChoiceField(queryset=Avatar.objects.all(), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-select tom-select'}))
    recompensa_bordas = forms.ModelMultipleChoiceField(queryset=Borda.objects.all(), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-select tom-select'}))
    recompensa_banners = forms.ModelMultipleChoiceField(queryset=Banner.objects.all(), required=False, widget=forms.SelectMultiple(attrs={'class': 'form-select tom-select'}))

    class Meta:
        model = Conquista
        fields = ['nome', 'trilha', 'descricao', 'icone', 'cor', 'is_secreta', 'pre_requisitos']
        widgets = {'nome': forms.TextInput(attrs={'class': 'form-control'}),'trilha': forms.Select(attrs={'class': 'form-select'}),'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),'icone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: fas fa-fire'}),'cor': forms.TextInput(attrs={'class': 'form-control', 'type': 'color', 'style': 'width: 100px;'}),'is_secreta': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),'pre_requisitos': forms.SelectMultiple(attrs={'class': 'form-select tom-select'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk: self.fields['pre_requisitos'].queryset = Conquista.objects.exclude(pk=self.instance.pk)
        if self.instance and self.instance.pk and self.instance.recompensas:
            recompensas = self.instance.recompensas
            self.fields['recompensa_xp'].initial = recompensas.get('xp')
            self.fields['recompensa_moedas'].initial = recompensas.get('moedas')
            self.fields['recompensa_avatares'].initial = Avatar.objects.filter(id__in=recompensas.get('avatares', []))
            self.fields['recompensa_bordas'].initial = Borda.objects.filter(id__in=recompensas.get('bordas', []))
            self.fields['recompensa_banners'].initial = Banner.objects.filter(id__in=recompensas.get('banners', []))


class CondicaoVolumeQuestoesForm(forms.ModelForm):
    class Meta:
        model = CondicaoVolumeQuestoes
        fields = ['quantidade', 'disciplina', 'assunto', 'banca', 'percentual_acerto_minimo']
        widgets = {
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'disciplina': forms.Select(attrs={'class': 'form-select'}),
            'assunto': forms.Select(attrs={'class': 'form-select'}),
            'banca': forms.Select(attrs={'class': 'form-select'}),
            'percentual_acerto_minimo': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class CondicaoStreakForm(forms.ModelForm):
    class Meta:
        model = CondicaoStreak
        fields = ['dias_consecutivos']
        widgets = {'dias_consecutivos': forms.NumberInput(attrs={'class': 'form-control'})}

# =======================================================================
# FORMULÁRIO DE CONCESSÃO MANUAL
# =======================================================================
class ConcessaoManualForm(forms.Form):
    TIPO_RECOMPENSA_CHOICES = [('', '---------'), ('MOEDAS', 'Moedas (Fragmentos de Conhecimento)'), ('AVATAR', 'Avatar'), ('BORDA', 'Borda'), ('BANNER', 'Banner')]
    usuario = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True, is_staff=False).select_related('userprofile'), label="Usuário", widget=forms.Select(attrs={'class': 'form-select tom-select-user'}), help_text="Selecione o usuário que receberá a recompensa.")
    tipo_recompensa = forms.ChoiceField(choices=TIPO_RECOMPENSA_CHOICES, label="Tipo de Recompensa", widget=forms.Select(attrs={'class': 'form-select'}))
    quantidade_moedas = forms.IntegerField(label="Quantidade de Moedas", required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    avatar = forms.ModelChoiceField(queryset=Avatar.objects.all().order_by('nome'), label="Avatar Específico", required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    borda = forms.ModelChoiceField(queryset=Borda.objects.all().order_by('nome'), label="Borda Específica", required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    banner = forms.ModelChoiceField(queryset=Banner.objects.all().order_by('nome'), label="Banner Específico", required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    justificativa = forms.CharField(label="Justificativa", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), help_text="Motivo da concessão (ex: prêmio de evento, correção de erro, etc.). Ficará registrado nos logs.")

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_recompensa')
        if tipo == 'MOEDAS' and not cleaned_data.get('quantidade_moedas'): self.add_error('quantidade_moedas', 'Este campo é obrigatório.')
        elif tipo == 'AVATAR' and not cleaned_data.get('avatar'): self.add_error('avatar', 'Este campo é obrigatório.')
        elif tipo == 'BORDA' and not cleaned_data.get('borda'): self.add_error('borda', 'Este campo é obrigatório.')
        elif tipo == 'BANNER' and not cleaned_data.get('banner'): self.add_error('banner', 'Este campo é obrigatório.')
        return cleaned_data

class TipoCondicaoForm(forms.ModelForm):
    """
    Formulário para que o admin crie e edite os Tipos de Condição
    disponíveis para as conquistas.
    """
    class Meta:
        model = TipoCondicao
        fields = ['nome', 'chave', 'descricao', 'parametros_configuraveis']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'chave': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'parametros_configuraveis': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }
        help_texts = {
            'chave': "Identificador único usado pelo sistema (ex: 'volume_questoes'). Deve ser único e sem espaços.",
            'parametros_configuraveis': "Defina os campos em formato JSON. Ex: {\"quantidade\": \"number\", \"disciplina\": \"select_disciplina\"}"
        }