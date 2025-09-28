# usuarios/utils.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import threading

class EmailThread(threading.Thread):
    """
    Classe para enviar e-mails em uma thread separada, prevenindo timeouts.
    Inclui logging para depuração em produção.
    """
    def __init__(self, email):
        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        try:
            self.email.send()
            print(f"Email para {self.email.to} enviado com sucesso em segundo plano.")
        except Exception as e:
            # Esta mensagem aparecerá nos logs do Render se algo der errado
            print(f"ERRO ao enviar e-mail em segundo plano para {self.email.to}: {e}")

def enviar_email_com_template(request, subject, template_name, context, recipient_list):
    """
    Renderiza um template HTML e o envia como um e-mail em uma thread separada
    para não bloquear a requisição principal.
    """
    context['host'] = request.get_host()
    
    html_content = render_to_string(template_name, context)
    
    email = EmailMultiAlternatives(
        subject=subject,
        body='', 
        from_email=settings.DEFAULT_FROM_EMAIL, # Usa o remetente verificado
        to=recipient_list
    )
    email.attach_alternative(html_content, "text/html")

    # Inicia a thread para enviar o e-mail sem bloquear a aplicação
    EmailThread(email).start()