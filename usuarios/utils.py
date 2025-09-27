# usuarios/utils.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import threading

# =======================================================================
# INÍCIO DA CORREÇÃO: Classe de Thread com log para depuração
# =======================================================================
class EmailThread(threading.Thread):
    def __init__(self, email):
        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        try:
            self.email.send()
            print(f"Email para {self.email.to} enviado com sucesso em segundo plano.")
        except Exception as e:
            # Esta mensagem aparecerá nos logs do Render se algo der errado!
            print(f"ERRO ao enviar e-mail em segundo plano para {self.email.to}: {e}")

# =======================================================================
# FIM DA CORREÇÃO
# =======================================================================

def enviar_email_com_template(request, subject, template_name, context, recipient_list):
    """
    Renderiza um template HTML e o envia como um e-mail em uma thread separada
    para não bloquear a requisição principal. Agora com logging.
    """
    context['host'] = request.get_host()
    
    html_content = render_to_string(template_name, context)
    
    email = EmailMultiAlternatives(
        subject=subject,
        body='', 
        from_email=settings.EMAIL_HOST_USER,
        to=recipient_list
    )
    email.attach_alternative(html_content, "text/html")

    # Inicia a thread com a nossa nova classe
    EmailThread(email).start()