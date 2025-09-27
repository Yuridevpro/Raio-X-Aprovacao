# usuarios/utils.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
# =======================================================================
# INÍCIO DA CORREÇÃO: Importando o módulo de threading
# =======================================================================
import threading
# =======================================================================
# FIM DA CORREÇÃO
# =======================================================================

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
        from_email=settings.EMAIL_HOST_USER,
        to=recipient_list
    )
    email.attach_alternative(html_content, "text/html")

    # =======================================================================
    # INÍCIO DA CORREÇÃO: Lógica de envio em segundo plano
    # =======================================================================
    # Em vez de chamar email.send() diretamente, criamos uma thread para fazer isso.
    # A função principal retorna imediatamente, e o e-mail é enviado em paralelo.
    thread = threading.Thread(target=email.send)
    thread.start()
    # =======================================================================
    # FIM DA CORREÇÃO
    # =======================================================================