# usuarios/utils.py
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def enviar_email_com_template(request, subject, template_name, context, recipient_list):
    """
    Renderiza um template HTML e o envia como um e-mail.
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
    email.send()