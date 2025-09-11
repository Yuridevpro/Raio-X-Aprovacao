# gestao/tests.py

from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from .models import DespromocaoSuperuser, ExclusaoSuperuser, PromocaoSuperuser
from questoes.models import Questao, Disciplina, Assunto
import json

class SuperuserQuorumModelTests(TestCase):
    # ... (esta classe permanece a mesma)
    def setUp(self):
        self.su1 = User.objects.create_superuser('su1', 'su1@test.com', 'password')
        self.su2 = User.objects.create_superuser('su2', 'su2@test.com', 'password')
        self.su3 = User.objects.create_superuser('su3', 'su3@test.com', 'password')
        self.staff_user = User.objects.create_user('staff', 'staff@test.com', 'password', is_staff=True)
        self.normal_user = User.objects.create_user('user', 'user@test.com', 'password')

    def test_despromocao_quorum_com_3_superusers(self):
        request = DespromocaoSuperuser.objects.create(solicitado_por=self.su1, usuario_alvo=self.su2, justificativa='teste')
        self.assertEqual(request.get_quorum_necessario(), 2)
    def test_despromocao_quorum_com_2_superusers(self):
        self.su3.delete()
        request = DespromocaoSuperuser.objects.create(solicitado_por=self.su1, usuario_alvo=self.su2, justificativa='teste')
        self.assertEqual(request.get_quorum_necessario(), 1)
    def test_despromocao_sucesso_com_quorum_atingido(self):
        request = DespromocaoSuperuser.objects.create(solicitado_por=self.su1, usuario_alvo=self.su3, justificativa='teste')
        status, message = request.aprovar(self.su2)
        self.assertEqual(status, 'QUORUM_MET')
        request.refresh_from_db()
        self.assertEqual(request.status, DespromocaoSuperuser.Status.APROVADO)
        self.su3.refresh_from_db()
        self.assertTrue(self.su3.is_superuser)
    def test_despromocao_falha_autoaprovacao_solicitante(self):
        request = DespromocaoSuperuser.objects.create(solicitado_por=self.su1, usuario_alvo=self.su2, justificativa='teste')
        status, message = request.aprovar(self.su1)
        self.assertEqual(status, 'FAILED')
        self.assertIn("solicitante não pode aprovar", message)
        self.su2.refresh_from_db()
        self.assertTrue(self.su2.is_superuser)
    def test_despromocao_sucesso_autoaprovacao_alvo_quorum_1(self):
        self.su3.delete()
        request = DespromocaoSuperuser.objects.create(solicitado_por=self.su1, usuario_alvo=self.su2, justificativa='teste')
        status, message = request.aprovar(self.su2)
        self.assertEqual(status, 'QUORUM_MET')
        request.refresh_from_db()
        self.assertEqual(request.status, DespromocaoSuperuser.Status.APROVADO)
    def test_exclusao_quorum_com_3_superusers(self):
        request = ExclusaoSuperuser.objects.create(solicitado_por=self.su1, usuario_alvo=self.su2, justificativa='teste')
        self.assertEqual(request.get_quorum_necessario(), 2)
    def test_exclusao_quorum_com_2_superusers(self):
        self.su3.delete()
        request = ExclusaoSuperuser.objects.create(solicitado_por=self.su1, usuario_alvo=self.su2, justificativa='teste')
        self.assertEqual(request.get_quorum_necessario(), 1)
    def test_exclusao_sucesso_com_quorum_atingido(self):
        request = ExclusaoSuperuser.objects.create(solicitado_por=self.su1, usuario_alvo=self.su3, justificativa='teste')
        status, message = request.aprovar(self.su2)
        self.assertEqual(status, 'QUORUM_MET')
        self.assertTrue(User.objects.filter(username='su3').exists())

@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
    MIDDLEWARE=[
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
        # O middleware do ratelimit não é necessário aqui, pois o decorador funciona de forma independente
    ]
)
class SuperuserSecurityViewTests(TestCase):
    
    def setUp(self):
        self.su1 = User.objects.create_superuser('su1', 'su1@test.com', 'password')
        self.su2 = User.objects.create_superuser('su2', 'su2@test.com', 'password')
        self.staff_user = User.objects.create_user('staff', 'staff@test.com', 'password', is_staff=True)
        self.normal_user = User.objects.create_user('user', 'user@test.com', 'password')

        disciplina = Disciplina.objects.create(nome='Teste')
        assunto = Assunto.objects.create(nome='Teste Assunto', disciplina=disciplina)
        self.questoes = [
            Questao.objects.create(disciplina=disciplina, assunto=assunto, enunciado=f'Q{i}', alternativas={}, gabarito='A')
            for i in range(15)
        ]
        
    def test_superuser_nao_pode_editar_outro_superuser_via_view(self):
        self.client.login(username='su1', password='password')
        url = reverse('gestao:editar_usuario_staff', args=[self.su2.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('gestao:listar_usuarios'))

    def test_staff_nao_pode_editar_superuser(self):
        self.client.login(username='staff', password='password')
        url = reverse('gestao:editar_usuario_staff', args=[self.su1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))

    def test_usuario_comum_nao_pode_acessar_view_de_aprovacao(self):
        request_obj = ExclusaoSuperuser.objects.create(solicitado_por=self.su1, usuario_alvo=self.su2, justificativa='teste')
        self.client.login(username='user', password='password')
        url = reverse('gestao:aprovar_exclusao_superuser', args=[request_obj.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))
        self.assertTrue(User.objects.filter(username='su2').exists())

    def test_view_bloqueia_exclusao_do_ultimo_superuser(self):
        User.objects.filter(is_superuser=True).exclude(pk__in=[self.su1.pk, self.su2.pk]).delete()
        self.client.login(username='su1', password='password')
        request_obj = ExclusaoSuperuser.objects.create(solicitado_por=self.su1, usuario_alvo=self.su2, justificativa='teste')
        url = reverse('gestao:aprovar_exclusao_superuser', args=[request_obj.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('gestao:listar_solicitacoes_exclusao_superuser'))
        self.assertTrue(User.objects.filter(username='su2').exists())

    def test_ratelimit_bloqueia_acoes_em_massa_excedidas(self):
        """
        Verifica se a view de ações em massa é bloqueada após exceder o limite de requisições.
        """
        self.client.login(username='staff', password='password')
        url = reverse('gestao:questoes_acoes_em_massa')
        
        payload = {
            'ids': [self.questoes[0].id],
            'action': 'delete',
        }
        payload_json = json.dumps(payload)

        for i in range(5):
            response = self.client.post(url, data=payload_json, content_type='application/json')
            self.assertEqual(response.status_code, 200, f"A chamada #{i+1} deveria passar, mas falhou.")

        # =======================================================================
        # CORREÇÃO FINAL: Esperar o status 403 retornado pela biblioteca
        # =======================================================================
        response = self.client.post(url, data=payload_json, content_type='application/json')
        self.assertEqual(response.status_code, 403, "A 6ª chamada deveria ser bloqueada com status 403, mas não foi.")
        # =======================================================================
        # FIM DA CORREÇÃO
        # =======================================================================